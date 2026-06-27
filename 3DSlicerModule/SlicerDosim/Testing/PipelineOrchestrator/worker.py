"""
PipelineWorker - Non-blocking step executor for 3Dosim pipelines.

Strategy:
- Light steps (< 5s): executed sequentially via QTimer chain with processEvents()
  between each step to keep Slicer UI responsive.
- Heavy steps (TotalSegmentator ~173s, Elastix ~60s, MCNP gen ~30s,
  MCTAL parse ~30s, PDF gen ~60s): executed in a daemon thread while
  a QTimer polls every 200ms calling slicer.app.processEvents() so
  the UI stays alive.

Usage:
    worker = PipelineWorker(steps=[
        ("load_dicom",  False, self._load_dicom),
        ("segment_ts",  True,  self._segment),  # heavy
        ("validate",    False, self._validate),
    ])
    worker.step_completed.connect(self._on_step_completed)
    worker.step_error.connect(self._on_step_error)
    worker.blocking_started.connect(self._on_blocking_started)
    worker.pipeline_completed.connect(self._on_pipeline_completed)
    worker.start()

Signals:
    step_started(name: str)
    step_completed(name: str, result: Any, elapsed_seconds: float)
    step_error(name: str, error_msg: str, elapsed_seconds: float)
    blocking_started(name: str)     # emitted when a heavy step begins
    pipeline_completed(name: str)   # all steps finished
"""

import logging
import threading
import time

logger = logging.getLogger("3DosimWorker")

# ──────────────────────────────────────────────────────────
# Qt imports (Slicer's bundled Qt)
# ──────────────────────────────────────────────────────────
try:
    from qt import QObject, Signal, QTimer
except ImportError:
    # Fallback for testing outside Slicer — signals become no-ops
    class Signal:
        def __init__(self, *types):
            self._handlers = []
        def connect(self, fn):
            self._handlers.append(fn)
        def emit(self, *args):
            for fn in self._handlers:
                fn(*args)

    class QObject:
        pass

    class QTimer:
        def __init__(self):
            self._fn = None
            self._single_shot = False
        def setSingleShot(self, v):
            self._single_shot = v
        def timeout(self, fn):
            self._fn = fn
        def start(self, ms):
            if self._fn:
                self._fn()
        def stop(self):
            pass
        def isActive(self):
            return False


class PipelineWorker(QObject):
    """
    Executes a list of (name, is_heavy, callable) steps in order.
    Light steps run in the main thread with processEvents() between.
    Heavy steps run in a daemon thread with QTimer polling at 200ms.
    """

    # Signals
    step_started = Signal(str)               # step_name
    step_completed = Signal(str, object, float)  # name, result, elapsed
    step_error = Signal(str, str, float)      # name, error_msg, elapsed
    blocking_started = Signal(str)            # name (threaded step began)
    pipeline_completed = Signal()

    POLL_INTERVAL_MS = 200  # poll every 200ms for thread completion

    def __init__(self, steps=None, parent=None):
        """
        Args:
            steps: list of (step_name: str, is_heavy: bool, callable)
            parent: optional QObject parent
        """
        super().__init__(parent)
        self._steps = steps or []
        self._index = -1
        self._aborted = False
        self._results = {}

        # Thread state
        self._thread = None
        self._thread_step_name = None
        self._thread_result = None
        self._thread_error = None

        # Timers
        self._chain_timer = QTimer()
        self._chain_timer.setSingleShot(True)
        self._chain_timer.timeout.connect(self._advance)

        self._poll_timer = QTimer()
        self._poll_timer.setInterval(self.POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_thread)

        # Start time tracking
        self._step_start_time = 0.0

    # ── Public API ────────────────────────────────────────────

    def start(self):
        """Begin executing steps from index 0."""
        self._index = -1
        self._aborted = False
        self._results = {}
        self._chain_timer.start(10)  # start chain on next event-loop tick

    def abort(self):
        """Stop execution immediately. No more steps will run."""
        self._aborted = True
        self._poll_timer.stop()
        self._chain_timer.stop()
        logger.warning("  [Worker] Pipeline abortado por el usuario")

    def is_running(self) -> bool:
        """True if the pipeline is still executing."""
        if self._chain_timer.isActive() or self._poll_timer.isActive():
            return True
        if self._thread and self._thread.is_alive():
            return True
        return self._index < len(self._steps) and not self._aborted

    def step_count(self) -> int:
        return len(self._steps)

    def current_step_index(self) -> int:
        return self._index

    def continue_on_error(self):
        """
        Call from a step_error handler to continue the chain despite the error.
        The failed step is recorded but the next step will execute.
        """
        if not self._aborted:
            self._chain_timer.start(10)

    # ── Internal chain ────────────────────────────────────────

    def _advance(self):
        """Execute the next step in the chain."""
        if self._aborted:
            return

        self._index += 1

        if self._index >= len(self._steps):
            logger.info("  [Worker] Pipeline completado — todos los pasos ejecutados")
            self.pipeline_completed.emit()
            return

        name, is_heavy, func = self._steps[self._index]

        # Process pending UI events before starting
        self._process_events()

        self._step_start_time = time.time()
        self.step_started.emit(name)

        logger.info(f"  [Worker] {'⚡' if is_heavy else '→'} Paso {self._index+1}/{len(self._steps)}: "
                    f"{name} {'[HEAVY - threaded]' if is_heavy else '[light]'}")

        if is_heavy:
            self.blocking_started.emit(name)
            self._run_heavy(name, func)
        else:
            self._run_light(name, func)

    def _run_light(self, name, func):
        """Execute a light step synchronously (with processEvents before/after)."""
        try:
            self._process_events()
            result = func()
            elapsed = time.time() - self._step_start_time
            self._results[name] = result
            logger.info(f"  [Worker] ✓ {name} completado en {elapsed:.1f}s")
            self.step_completed.emit(name, result, elapsed)
        except Exception as e:
            elapsed = time.time() - self._step_start_time
            logger.error(f"  [Worker] ✗ {name} FALLO: {e}")
            self.step_error.emit(name, str(e), elapsed)
            return  # chain stops — handler can call continue_on_error()

        # Continue chain on next tick
        self._chain_timer.start(10)

    def _run_heavy(self, name, func):
        """Launch a heavy step in a daemon thread. Polling takes over."""
        self._thread_step_name = name
        self._thread_result = None
        self._thread_error = None
        self._thread = threading.Thread(
            target=self._thread_wrapper,
            args=(func,),
            daemon=True,
            name=f"3Dosim-{name}",
        )
        self._thread.start()
        logger.info(f"  [Worker] Thread launched para '{name}' — polling cada "
                     f"{self.POLL_INTERVAL_MS}ms")
        self._poll_timer.start()

    def _thread_wrapper(self, func):
        """Wrapper that captures the result or exception from a heavy step."""
        try:
            # Heavy steps typically don't access Slicer MRML nodes directly.
            # TotalSegmentator, Elastix, PDF generation, MCTAL parsing,
            # and MCNP generation all run their own computations without
            # touching the Slicer scene (nodes are pre-created in main thread).
            result = func()
            self._thread_result = result
        except Exception as e:
            self._thread_error = e

    def _poll_thread(self):
        """Called every POLL_INTERVAL_MS to check if the heavy thread finished."""
        self._process_events()

        if self._thread is None or self._thread.is_alive():
            return  # still running

        # Thread finished
        self._poll_timer.stop()
        name = self._thread_step_name
        elapsed = time.time() - self._step_start_time

        if self._thread_error:
            logger.error(f"  [Worker] ✗ {name} FALLO en thread: {self._thread_error}")
            self.step_error.emit(name, str(self._thread_error), elapsed)
        else:
            self._results[name] = self._thread_result
            logger.info(f"  [Worker] ✓ {name} completado en {elapsed:.1f}s (threaded)")
            self.step_completed.emit(name, self._thread_result, elapsed)
            # Continue chain
            self._chain_timer.start(10)

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _process_events():
        """Process pending Qt events to keep Slicer UI responsive."""
        try:
            import slicer
            slicer.app.processEvents()
        except ImportError:
            pass
