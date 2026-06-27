"""
PipelineMod2 - Modulo 2: Generacion de entrada MCNP desde escena Mod1.
Flujo: carga escena .mrb, escanea nodos, genera input MCNP, valida.

NO incluye carga DICOM/segmentacion/tumor (eso es Mod1).
NO incluye analisis dosimetrico (eso es Mod3).

Sigue el mismo patron que PipelineMod1 (CheckpointManager, _checkpoint_step, etc.).
"""

import logging
import os
import time

from PipelineOrchestrator.checkpoint import CheckpointManager
from PipelineOrchestrator.worker import PipelineWorker
from PipelineOrchestrator.utils import logger as base_logger, add_module_path, show_progress
from PipelineOrchestrator.views import load_pipeline_config

logger = logging.getLogger("3DosimMod2")

# ──────────────────────────────────────────────────────────
# Progress helper (barra simple para consola)
# ──────────────────────────────────────────────────────────

class QProgressHelper:
    """Barra de progreso Qt visible dentro de 3D Slicer.

    Muestra un QProgressDialog real que el usuario puede ver.
    Fallback a consola si no estamos en Slicer.
    """
    def __init__(self, label="Procesando", max_seconds=120, can_cancel=False):
        self.label = label
        self.start = time.time()
        self._dialog = None
        self._use_qt = False
        try:
            import slicer
            from qt import QProgressDialog, QApplication
            self._dialog = QProgressDialog(label, "", 0, 100)
            self._dialog.setWindowTitle("3Dosim - Modulo 2")
            self._dialog.setMinimumDuration(0)  # mostrar inmediatamente
            self._dialog.setCancelButton(None)  # sin boton de cancelar
            if not can_cancel:
                self._dialog.setCancelButton(None)
            self._dialog.show()
            QApplication.processEvents()
            self._use_qt = True
        except ImportError:
            pass  # fallback a consola

    def update(self, pct, msg=""):
        """Actualiza progreso (pct: 0-100)."""
        elapsed = time.time() - self.start
        if self._use_qt and self._dialog:
            self._dialog.setValue(pct)
            self._dialog.setLabelText(f"{msg}\n{elapsed:.0f}s transcurridos")
            try:
                from qt import QApplication
                QApplication.processEvents()
            except ImportError:
                pass
        else:
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  {self.label}: |{bar}| {pct}%  {msg}  [{elapsed:.0f}s]", end="")
            if pct >= 100:
                print()

    def done(self, msg="Completado"):
        """Cierra el dialogo de progreso."""
        elapsed = time.time() - self.start
        if self._use_qt and self._dialog:
            self._dialog.setValue(100)
            self._dialog.setLabelText(f"{msg} ({elapsed:.0f}s)")
            try:
                from qt import QApplication
                QApplication.processEvents()
            except ImportError:
                pass
            self._dialog.close()
            self._dialog = None
        else:
            print(f"  {self.label}: {msg} [{elapsed:.0f}s]")


# ──────────────────────────────────────────────────────────
# PipelineMod2 class
# ──────────────────────────────────────────────────────────

class PipelineMod2:
    """
    Pipeline Modulo 2: carga escena .mrb (generada por Mod1),
    escanea nodos y genera entrada MCNP.
    """

    STEP_CHECK_SLICER  = "check_slicer"
    STEP_LOAD_SCENE    = "load_scene"
    STEP_SCAN_NODES    = "scan_nodes"
    STEP_GENERATE_MCNP = "generate_mcnp"
    STEP_VALIDATE_MCNP = "validate_mcnp"

    def __init__(self, scene_path=None, output_dir=None, reset=False,
                 isotope="Y-90", n_particles=int(1e7),
                 flip_rows=True, flip_z=False, refine_hu=False,
                 n_liver_tallies=5, n_tumor_tallies=10):
        """
        Args:
            scene_path: Ruta al archivo .mrb (de Mod1). Si None, auto-detecta.
            output_dir: Directorio de salida. Si None, usa junto a scene_path.
            reset: Si True, reinicia checkpoints.
            isotope: Isotopo para la fuente (Y-90, I-131, Lu-177, Tc-99m).
            n_particles: Numero de historias MCNP.
            flip_rows: Invertir eje Y antes de RLE.
            flip_z: Invertir eje Z.
            refine_hu: Refinar mapeo HU -> materiales.
            n_liver_tallies: Numero de tallies de higado en FMESH4.
            n_tumor_tallies: Numero de tallies de tumor en FMESH4.
        """
        # ── Scene path ──
        self.scene_path = scene_path or self._auto_detect_scene()
        if not self.scene_path or not os.path.exists(self.scene_path):
            logger.warning("No se encontro escena .mrb. Se requiere --scene al ejecutar.")

        # ── Output dir ──
        if output_dir:
            self.output_dir = output_dir
        elif self.scene_path:
            scene_parent = os.path.dirname(os.path.dirname(self.scene_path))
            self.output_dir = scene_parent  # scenes/ -> ai-pipe/
        else:
            self.output_dir = r"C:\MAT\3Dosim\ai-pipe"

        self.mcnp_dir = os.path.join(self.output_dir, "mcnp_input")
        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints", "mod2")
        self.results = {"pasos": [], "errores": [], "tiempos": {}}

        self.checkpoint = CheckpointManager(self.checkpoint_dir)
        if reset:
            self.checkpoint.reset()

        # ── MCNP params ──
        self.isotope = isotope
        self.n_particles = n_particles
        self.flip_rows = flip_rows
        self.flip_z = flip_z
        self.refine_hu = refine_hu
        self.n_liver_tallies = n_liver_tallies
        self.n_tumor_tallies = n_tumor_tallies
        self.mcnp_output_path = None

        # ── Nodos (se llenan en scan_nodes) ──
        self.ct_node = None
        self.ct_masked_node = None
        self.pet_node = None
        self.segmentation_node = None

        # ── Config ──
        self.pipeline_config = load_pipeline_config()
        self.scene_output_dir = self.pipeline_config.get(
            "scene_output_dir",
            os.path.join(self.output_dir, "scenes"),
        )

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Modulo 2 — Generacion MCNP")
        logger.info("=" * 60)
        logger.info(f"  Escena:       {self.scene_path or 'NO DISPONIBLE'}")
        logger.info(f"  Output:       {self.mcnp_dir}")
        logger.info(f"  Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"  Isotopo:      {isotope}")
        logger.info(f"  Particulas:   {n_particles:.0e}")
        logger.info(f"  Flip Y:       {flip_rows}")
        logger.info(f"  Flip Z:       {flip_z}")
        logger.info(f"  Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info("")

    # ==================================================================
    # RUN (blocking — backward compatible)
    # ==================================================================

    def run(self):
        """Ejecuta el pipeline Mod2 de forma BLOQUEANTE.

        Usa PipelineWorker internamente pero se bloquea hasta que
        todos los pasos terminen. Compatible con entry points existentes.
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 2")
        logger.info("")

        if not self.scene_path or not os.path.exists(self.scene_path):
            logger.error("No hay escena .mrb disponible. Abortando.")
            logger.error("Use --scene <path> o ejecute Mod1 primero.")
            self._report()
            return

        # Construir worker
        self._build_worker()

        # Bloquear hasta que termine
        self._pipeline_ok = False
        self._pipeline_done = False

        try:
            from qt import QEventLoop
            self.worker.pipeline_completed.connect(lambda: setattr(self, '_pipeline_ok', True))
            self.worker.pipeline_completed.connect(lambda: setattr(self, '_pipeline_done', True))
            self.worker.step_error.connect(lambda n, e, t: setattr(self, '_pipeline_ok', False))
            self.worker.start()

            loop = QEventLoop()
            self.worker.pipeline_completed.connect(loop.quit)
            self.worker.step_error.connect(lambda n, e, t: loop.quit())
            loop.exec_()
        except ImportError:
            self.worker.start()
            import time
            while self.worker.is_running():
                time.sleep(0.1)

        ok = self._pipeline_ok
        if ok:
            logger.info("Modulo 2 finalizado EXITOSAMENTE")
        else:
            logger.info("Modulo 2 finalizado con ERRORES. Revise el reporte.")

    # ────────────────────────────────────────────────────────────
    # RUN ASYNC (non-blocking)
    # ────────────────────────────────────────────────────────────

    def run_async(self, on_completed=None, on_error=None):
        """
        Ejecuta el pipeline Mod2 de forma NO BLOQUEANTE.

        Args:
            on_completed: callback(success: bool)
            on_error: callback(step_name: str, error: str)
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 2 (async)")
        logger.info("")

        if not self.scene_path or not os.path.exists(self.scene_path):
            logger.error("No hay escena .mrb disponible.")
            if on_error:
                on_error("scene_check", "Escena .mrb no encontrada")
            return

        self._build_worker()

        if on_completed:
            self.worker.pipeline_completed.connect(
                lambda: on_completed(getattr(self, '_pipeline_ok', False)))
        if on_error:
            self.worker.step_error.connect(
                lambda name, err, elapsed: on_error(name, err))

        self._pipeline_ok = False
        self.worker.pipeline_completed.connect(lambda: setattr(self, '_pipeline_ok', True))
        self.worker.start()

        logger.info("  [Async] Pipeline Mod2 iniciado — Slicer responde durante la ejecucion")

    # ────────────────────────────────────────────────────────────
    # BUILD WORKER
    # ────────────────────────────────────────────────────────────

    def _build_worker(self):
        """Construye el PipelineWorker con los pasos de Mod2."""
        steps = []

        # Paso 1: check_slicer
        steps.append((self.STEP_CHECK_SLICER, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_CHECK_SLICER, "Verificando entorno Slicer",
                          self._check_slicer,
                          data_func=lambda: {"slicer_version": self._slicer_version()},
                          post_fn=lambda: add_module_path())))

        # Paso 2: load_scene (SIEMPRE se ejecuta, no checkpointeable)
        steps.append(("load_scene", False,
                      lambda: self._always_run_step(
                          "load_scene", "Cargando escena .mrb", self._load_scene,
                          critical=True)))

        # Paso 3: scan_nodes (SIEMPRE se ejecuta)
        steps.append(("scan_nodes", False,
                      lambda: self._always_run_step(
                          "scan_nodes", "Escaneando nodos de la escena", self._scan_nodes,
                          critical=True)))

        # Paso 4: generate_mcnp (~30s → HEAVY)
        steps.append((self.STEP_GENERATE_MCNP, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_GENERATE_MCNP, "Generando entrada MCNP",
                          self._generate_mcnp,
                          critical=True,
                          data_func=lambda: {
                              "isotope": self.isotope,
                              "n_particles": self.n_particles,
                              "output_path": self.mcnp_output_path,
                          },
                          post_fn=lambda: self._save_scene("02_post_mcnp"))))

        # Paso 5: validate_mcnp (light)
        steps.append((self.STEP_VALIDATE_MCNP, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_VALIDATE_MCNP, "Validando archivo MCNP",
                          self._validate_mcnp,
                          data_func=lambda: {
                              "mcnp_path": self.mcnp_output_path,
                              "exists": os.path.exists(self.mcnp_output_path) if self.mcnp_output_path else False,
                          })))

        self.worker = PipelineWorker(steps)

        # ── Conectar señales ──
        self.worker.step_completed.connect(self._on_worker_step_completed)
        self.worker.step_error.connect(self._on_worker_step_error)
        self.worker.blocking_started.connect(self._on_worker_blocking_started)
        self.worker.pipeline_completed.connect(self._on_worker_pipeline_completed)

    # ────────────────────────────────────────────────────────────
    # WORKER SIGNAL HANDLERS
    # ────────────────────────────────────────────────────────────

    def _on_worker_step_completed(self, name, result, elapsed):
        logger.info(f"  [Worker] Paso '{name}' OK ({elapsed:.1f}s)")

    def _on_worker_step_error(self, name, error_msg, elapsed):
        logger.error(f"  [Worker] Paso '{name}' FALLO: {error_msg}")

    def _on_worker_blocking_started(self, name):
        logger.info(f"  [Worker] Iniciando paso pesado: {name} (thread)")

    def _on_worker_pipeline_completed(self):
        """Todos los pasos terminaron."""
        errores = self.results.get("errores", [])
        has_fatal = any("CRITICO" in e for e in errores)

        logger.info("")
        logger.info("  PIPELINE MODULO 2 COMPLETADO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. Verificar Slicer")
        logger.info("    2. Cargar escena .mrb desde Mod1")
        logger.info("    3. Escanear nodos (CT, PET, Segmentacion)")
        logger.info("    4. Generar entrada MCNP")
        logger.info("    5. Validar archivo MCNP generado")
        logger.info("")
        logger.info("  Siguiente paso:")
        logger.info("    Modulo 3: analisis dosimetrico desde output MCNP")
        logger.info("")

        ok = not has_fatal
        self._report()

    # ────────────────────────────────────────────────────────────
    # WRAPPER: checkpoint_step unificado (igual que Mod1)
    # ────────────────────────────────────────────────────────────

    def _checkpoint_step_wrapper(self, step_name, display_name, func,
                                  data_func=None, critical=False, post_fn=None):
        """Wrapper unificado con checkpoint, timing, registro y post-action."""
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            cp_data = self.checkpoint.get_data(step_name)
            if cp_data:
                self._restore_step_state(step_name, cp_data)
            if post_fn:
                try:
                    post_fn()
                except Exception as e:
                    logger.debug(f"Post-step checkpoint skip fallo: {e}")
            return True

        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        show_progress(f"Ejecutando: {display_name}")

        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed
            })
            self.results["tiempos"][display_name] = elapsed
            data = data_func() if data_func else {}
            self.checkpoint.mark_completed(step_name, data=data)
            show_progress(f"{display_name} completado")

            if post_fn:
                try:
                    post_fn()
                except Exception as e:
                    logger.warning(f"Post-step handler fallo: {e}")

            return True
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  FALLO: {e}")
            self.results["pasos"].append({
                "nombre": display_name, "ok": False, "tiempo": elapsed
            })
            error_msg = f"{display_name}: {e}"
            if critical:
                error_msg = f"[CRITICO] {error_msg}"
            self.results["errores"].append(error_msg)
            show_progress(f"FALLO: {display_name}")
            if critical:
                logger.error(f"  [CRITICO] {display_name} fallo — abortando")
                self.worker.abort()
            return False

    def _always_run_step(self, name, display_name, func, critical=False):
        """
        Ejecuta un paso que SIEMPRE corre (no checkpointeable).
        Registra el resultado en self.results["pasos"].
        """
        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        show_progress(f"Ejecutando: {display_name}")
        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed
            })
            show_progress(f"{display_name} completado")
            return True
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  FALLO: {e}")
            self.results["pasos"].append({
                "nombre": display_name, "ok": False, "tiempo": elapsed
            })
            error_msg = f"{display_name}: {e}"
            if critical:
                error_msg = f"[CRITICO] {error_msg}"
                logger.error(f"  [CRITICO] {display_name} fallo — abortando")
            self.results["errores"].append(error_msg)
            show_progress(f"FALLO: {display_name}")
            if critical:
                self.worker.abort()
            raise  # re-raise to let worker handle signal emission

    def _slicer_version(self) -> str:
        try:
            import slicer
            return f"{slicer.app.majorVersion}.{slicer.app.minorVersion}"
        except ImportError:
            return "desconocido"

    # ==================================================================
    # CHECKPOINT + HELPERS (mismo patron que PipelineMod1)
    # ==================================================================

    def _checkpoint_step(self, step_name, display_name, func, data_func=None):
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            cp_data = self.checkpoint.get_data(step_name)
            if cp_data:
                self._restore_step_state(step_name, cp_data)
            return True

        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        show_progress(f"Ejecutando: {display_name}")

        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed
            })
            self.results["tiempos"][display_name] = elapsed
            data = data_func() if data_func else {}
            self.checkpoint.mark_completed(step_name, data=data)
            show_progress(f"{display_name} completado")
            return True
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  FALLO: {e}")
            self.results["pasos"].append({
                "nombre": display_name, "ok": False, "tiempo": elapsed
            })
            self.results["errores"].append(f"{display_name}: {e}")
            show_progress(f"FALLO: {display_name}")
            return False

    def _restore_step_state(self, step_name, data):
        """Restaura estado desde checkpoint data.

        Soporta dos formatos:
        - Nuevo: ``{"ct_node_name": "nombre"}`` → ``slicer.util.getNode("nombre")``
        - Viejo: ``{"ct_node": "nombre"}`` → mismo lookup, para compatibilidad

        NOTA: Si la escena no esta cargada (checkpoint load_scene salteado
        y Slicer fresh), este metodo fallara silenciosamente y los nodos
        quedaran en None. Por eso load_scene se ejecuta SIEMPRE (ver run()).
        """
        if not data:
            return
        import slicer
        # Mapeo de compatibilidad: keys viejos del checkpoint → attr actual
        compat_keys = {"seg_node": "segmentation_node"}
        # Restaurar nodos
        for key in ["ct_node", "pet_node", "segmentation_node"]:
            name_key = key + "_name"
            node_name = None
            # Nuevo formato: _name suffix
            if name_key in data and data[name_key] is not None:
                node_name = data[name_key]
            # Viejo formato 1: key directo con string (ej: "ct_node": "nombre")
            elif key in data and isinstance(data[key], str) and data[key]:
                node_name = data[key]
            # Viejo formato 2: key legacy (ej: "seg_node": "nombre")
            for old_key, mapped_key in compat_keys.items():
                if mapped_key == key and old_key in data and isinstance(data[old_key], str) and data[old_key]:
                    node_name = data[old_key]
                    break
            if node_name:
                try:
                    node = slicer.util.getNode(node_name)
                    setattr(self, key, node)
                except Exception:
                    pass
        if self.mcnp_output_path is None and data.get("output_path"):
            self.mcnp_output_path = data["output_path"]

    def _save_scene(self, tag=None):
        """Guarda escena .mrb actual."""
        try:
            import slicer
            filename = "3Dosim_mod2_scene.mrb"
            scene_dir = getattr(self, "scene_output_dir", None)
            if not scene_dir:
                scene_dir = os.path.join(self.output_dir, "scenes")
            os.makedirs(scene_dir, exist_ok=True)
            filepath = os.path.join(scene_dir, filename)

            old_tmp = os.environ.get("TMP", "")
            old_temp = os.environ.get("TEMP", "")
            try:
                short_tmp = r"C:\tmp"
                os.makedirs(short_tmp, exist_ok=True)
                os.environ["TMP"] = short_tmp
                os.environ["TEMP"] = short_tmp
                success = slicer.util.saveScene(filepath)
            finally:
                os.environ["TMP"] = old_tmp
                os.environ["TEMP"] = old_temp

            if success:
                logger.info(f"  Escena{' ['+tag+']' if tag else ''} guardada: {os.path.basename(filepath)}")
                return filepath
        except Exception as e:
            logger.warning(f"No se pudo guardar escena '{tag}': {e}")
            return None

    def _save_results_json(self):
        """Guarda resultados en JSON (historial acumulado)."""
        import json
        from datetime import datetime
        results_file = os.path.join(self.output_dir, "pipeline_results.json")
        historial = []
        if os.path.exists(results_file):
            try:
                with open(results_file, "r") as f:
                    historial = json.load(f)
                    if not isinstance(historial, list):
                        historial = [historial]
            except (json.JSONDecodeError, Exception):
                historial = []
        total = len(self.results["pasos"])
        ok_count = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok_count
        registro = {
            "fecha": datetime.now().isoformat(),
            "modulo": "Mod2",
            "scene_path": self.scene_path,
            "output_dir": self.output_dir,
            "isotope": self.isotope,
            "n_particles": self.n_particles,
            "total_pasos": total,
            "exitosos": ok_count,
            "fallos": fails,
            "resultado": "OK" if fails == 0 else "ERROR",
            "mcnp_output": self.mcnp_output_path,
            "pasos": self.results["pasos"],
            "errores": self.results["errores"],
        }
        historial.append(registro)
        with open(results_file, "w") as f:
            json.dump(historial, f, indent=2, default=str)
        logger.info(f"  Resultados guardados en: {results_file}")

    def _report(self) -> bool:
        """Genera reporte final."""
        try:
            self._save_results_json()
        except Exception as e:
            logger.warning(f"No se pudo guardar results.json: {e}")
        logger.info("")
        logger.info("=" * 70)
        logger.info(" REPORTE FINAL - MODULO 2")
        logger.info("=" * 70)
        total = len(self.results["pasos"])
        ok_count = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok_count
        skipped = sum(1 for p in self.results["pasos"] if p.get("checkpoint"))
        logger.info(f"  Pasos totales:     {total}")
        logger.info(f"  Exitosos:          {ok_count}")
        logger.info(f"  Desde checkpoint:  {skipped}")
        logger.info(f"  Fallos:            {fails}")
        if fails > 0:
            logger.info("  ERRORES:")
            for err in self.results["errores"]:
                logger.info(f"    - {err}")
        logger.info("  DETALLE DE PASOS:")
        logger.info("-" * 70)
        for paso in self.results["pasos"]:
            status = "+" if paso["ok"] else "-"
            cp = " (checkpoint)" if paso.get("checkpoint") else ""
            tiempo = f"{paso['tiempo']:.1f}s" if paso['tiempo'] > 0 else "-"
            logger.info(f"  {status} {paso['nombre']:<45s} {tiempo:>8s}{cp}")
        if self.mcnp_output_path and os.path.exists(self.mcnp_output_path):
            size_kb = os.path.getsize(self.mcnp_output_path) / 1024
            logger.info(f"  Archivo MCNP: {self.mcnp_output_path}")
            logger.info(f"  Tamano:       {size_kb:.1f} KB")
        logger.info(f"  Output: {self.mcnp_dir}")
        all_ok = fails == 0
        if all_ok:
            logger.info("  RESULTADO: TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f"  RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)
        return all_ok

    # ==================================================================
    # STEP METHODS
    # ==================================================================

    def _check_slicer(self):
        """Verifica que estamos dentro de 3D Slicer."""
        try:
            import slicer
            version = f"{slicer.app.majorVersion}.{slicer.app.minorVersion}"
            logger.info(f"  Slicer version: {version}")
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    def _load_scene(self):
        """Carga escena .mrb con barra de progreso."""
        import slicer

        if not os.path.exists(self.scene_path):
            raise FileNotFoundError(f"Escena no encontrada: {self.scene_path}")

        size_mb = os.path.getsize(self.scene_path) / (1024 * 1024)
        logger.info(f"  Escena: {self.scene_path}")
        logger.info(f"  Tamano: {size_mb:.0f} MB")

        pb = QProgressHelper("Cargando escena", max_seconds=60)
        pb.update(10, "Iniciando...")

        try:
            slicer.app.processEvents()
            pb.update(30, "Leyendo archivo MRB...")
            slicer.app.processEvents()

            success = slicer.util.loadScene(self.scene_path)

            pb.update(80, "Procesando nodos...")
            slicer.app.processEvents()

            if not success:
                raise RuntimeError("slicer.util.loadScene() devolvio False")
            pb.done("Escena cargada OK")
        except Exception as e:
            pb.done(f"ERROR: {e}")
            raise

        logger.info("  Escena cargada exitosamente")

    def _scan_nodes(self):
        """Busca nodos CT, PET y Segmentacion en la escena cargada."""
        import slicer
        import vtk

        vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        seg_nodes_list = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        lb_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")

        logger.info(f"  Volumenes: {len(vol_nodes)}, Segmentaciones: {len(seg_nodes_list)}, LabelMaps: {len(lb_nodes)}")

        # ── CT ──
        ct_candidates = [n for n in vol_nodes if "CT" in n.GetName() or "ct" in n.GetName().lower()]
        if ct_candidates:
            preferred = [n for n in ct_candidates if "anon" in n.GetName().lower() or "sin_camilla" in n.GetName().lower()]
            self.ct_node = preferred[0] if preferred else ct_candidates[0]
            logger.info(f"  CT: '{self.ct_node.GetName()}'")
        elif vol_nodes:
            self.ct_node = vol_nodes[0]
            logger.info(f"  CT (fallback): '{self.ct_node.GetName()}'")
        else:
            raise RuntimeError("No se encontraron volumenes CT en la escena")

        # ── CT_masked (opcional) ──
        masked = [n for n in vol_nodes if "sin_camilla" in n.GetName().lower() or "masked" in n.GetName().lower()]
        if masked:
            self.ct_masked_node = masked[0]
            logger.info(f"  CT_masked: '{self.ct_masked_node.GetName()}'")

        # ── PET (opcional) ──
        pet_candidates = [n for n in vol_nodes if "PET" in n.GetName() or "pet" in n.GetName().lower()]
        if pet_candidates:
            self.pet_node = pet_candidates[0]
            logger.info(f"  PET: '{self.pet_node.GetName()}'")
        else:
            self.pet_node = None
            logger.info("  PET: No encontrado (fuente uniforme)")

        # ── Segmentacion ──
        seg_found = None

        # Prioridad 1: labelmap pre-exportada por Mod1 ("3Dosim_Labelmap")
        # Ya tiene TODOS los indices correctos (30=Tejido_blando, 50=Pulmon,
        # 80=Hueso, 90=Higado, 100=Tumor) y NO necesita re-extraccion.
        preferred_lb = [n for n in lb_nodes if "3Dosim_Labelmap" in n.GetName()]
        if preferred_lb:
            seg_found = preferred_lb[0]
            logger.info(f"  Labelmap dosimetrica: '{seg_found.GetName()}' (preferida)")
            logger.info(f"    Usando labelmap ya exportada con indices del tissue_config")
        elif seg_nodes_list:
            ts_candidates = [n for n in seg_nodes_list if "TotalSegmentator" in n.GetName() or "Segmentation" in n.GetName()]
            seg_found = ts_candidates[0] if ts_candidates else seg_nodes_list[0]
            logger.info(f"  Segmentacion: '{seg_found.GetName()}'")
            # Contar segmentos
            seg_ids = vtk.vtkStringArray()
            seg_found.GetSegmentation().GetSegmentIDs(seg_ids)
            n_segs = seg_ids.GetNumberOfValues()
            logger.info(f"    Segmentos: {n_segs}")
        elif lb_nodes:
            seg_found = lb_nodes[0]
            logger.info(f"  Segmentacion (labelmap fallback): '{seg_found.GetName()}'")
        else:
            raise RuntimeError("No se encontraron nodos de segmentacion en la escena")

        self.segmentation_node = seg_found

    def _generate_mcnp(self):
        """Genera archivo de entrada MCNP usando MCNPInputGenerator."""
        try:
            from SlicerDosim.SlicerDosimLib import MCNPInputGenerator
        except ImportError:
            from SlicerDosimLib import MCNPInputGenerator

        generator = MCNPInputGenerator()

        logger.info(f"\n  Isotopo:       {self.isotope}")
        logger.info(f"  Particulas:    {self.n_particles:.0e}")
        logger.info(f"  Flip rows:     {self.flip_rows}")
        logger.info(f"  Output dir:    {self.mcnp_dir}")

        os.makedirs(self.mcnp_dir, exist_ok=True)

        pb = QProgressHelper("Generando MCNP", max_seconds=180)
        pb.update(5, "Iniciando...")

        input_path = generator.generate(
            ct_volume_node=self.ct_node,
            pet_volume_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            output_dir=self.mcnp_dir,
            isotope=self.isotope,
            n_particles=self.n_particles,
            refine_hu=self.refine_hu,
            flip_rows=self.flip_rows,
            flip_z=self.flip_z,
            n_liver_tallies=self.n_liver_tallies,
            n_tumor_tallies=self.n_tumor_tallies,
        )

        pb.done(f"Archivo MCNP generado ({os.path.getsize(input_path)/1024:.0f} KB)")

        if not os.path.exists(input_path):
            raise RuntimeError(f"El archivo MCNP no fue creado: {input_path}")

        file_size_kb = os.path.getsize(input_path) / 1024
        logger.info(f"\n  {'='*50}")
        logger.info(f"  ARCHIVO MCNP: {input_path}")
        logger.info(f"  Tamano: {file_size_kb:.1f} KB")
        logger.info(f"  {'='*50}\n")

        self.mcnp_output_path = input_path

    def _validate_mcnp(self):
        """Valida que el archivo MCNP generado sea correcto."""
        if not self.mcnp_output_path or not os.path.exists(self.mcnp_output_path):
            raise RuntimeError("Archivo MCNP no encontrado para validar")

        file_size_kb = os.path.getsize(self.mcnp_output_path) / 1024
        logger.info(f"  Validando: {self.mcnp_output_path}")
        logger.info(f"  Tamano:    {file_size_kb:.1f} KB")

        issues = []

        # Verificar tamano minimo
        if file_size_kb < 10:
            issues.append(f"Archivo MCNP muy pequeno: {file_size_kb:.1f} KB")

        # Verificar contenido basico
        try:
            with open(self.mcnp_output_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(5000)  # Leer primeras ~5000 lines

            lines = content.split("\n")
            logger.info(f"  Lineas: {len(lines)} (primeras 5000)")

            # Verificar palabras clave esenciales
            checks = {
                "cell card": "c cell" in content.lower() or "cell" in content.lower(),
                "surface card": "c surface" in content.lower() or "surface" in content.lower(),
                "data card": "c data" in content.lower(),
                "mode": "mode" in content.lower(),
                "nps": "nps" in content.lower() or "ctme" in content.lower(),
                "tally": "fmesh" in content.lower() or "f6" in content.lower() or "f4" in content.lower(),
            }

            logger.info("  Verificando palabras clave MCNP:")
            for check_name, found in checks.items():
                status = "OK" if found else "AUSENTE"
                logger.info(f"    {check_name}: {status}")
                if not found:
                    issues.append(f"Palabra clave '{check_name}' no encontrada")

            # Verificar primer caracter (debe ser mensaje o celda)
            first_line = lines[0].strip() if lines else ""
            if first_line and not first_line.startswith("c ") and not first_line.startswith("1"):
                logger.info(f"  (Primera linea no es comentario: '{first_line[:60]}')")

        except Exception as e:
            issues.append(f"Error leyendo archivo MCNP: {e}")

        if issues:
            logger.warning("  POTENCIALES PROBLEMAS:")
            for issue in issues:
                logger.warning(f"    - {issue}")
            # No lanzamos excepcion, solo reportamos
            logger.info("  Validacion completada con advertencias")
        else:
            logger.info("  Validacion: TODAS LAS VERIFICACIONES PASARON")

        return len(issues) == 0

    # ==================================================================
    # AUTO-DETECT
    # ==================================================================

    @staticmethod
    def _auto_detect_scene():
        """Auto-detecta la escena .mrb mas reciente."""
        base = r"C:\MAT\3Dosim\ai-pipe\scenes"
        candidates = [
            os.path.join(base, "3Dosim.mrb"),         # nombre actual Mod1
            os.path.join(base, "3Dosim_mod1_scene.mrb"),
            os.path.join(base, "3Dosim_scene.mrb"),
            r"C:\MAT\3Dosim\pacientes-\pacientes\resultados_test\scenes\3Dosim.mrb",
        ]
        newest = None
        newest_time = 0
        for c in candidates:
            if os.path.exists(c):
                mtime = os.path.getmtime(c)
                if mtime > newest_time:
                    newest = c
                    newest_time = mtime
        if newest:
            logger.info(f"  Escena auto-detectada: {newest}")
        else:
            logger.warning("  No se pudo auto-detectar escena .mrb")
        return newest


# ──────────────────────────────────────────────────────────
# CLI entry point (para ejecucion directa)
# ──────────────────────────────────────────────────────────

def main():
    """Entry point CLI para PipelineMod2."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Pipeline Mod2 - Generacion MCNP desde escena .mrb")
    parser.add_argument("--scene", default=None, help="Ruta al archivo .mrb")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--reset", action="store_true", help="Reiniciar checkpoints")
    parser.add_argument("--isotope", default="Y-90", help="Isotopo (Y-90, I-131, Lu-177, Tc-99m)")
    parser.add_argument("--n-particles", type=float, default=1e7, help="Numero de historias")
    parser.add_argument("--flip", action="store_true", default=True, help="Flip Y")
    parser.add_argument("--no-flip", action="store_false", dest="flip", help="No flip Y")
    parser.add_argument("--flip-z", action="store_true", help="Flip Z")
    parser.add_argument("--refine-hu", action="store_true", help="Refinar HU")
    args, _ = parser.parse_known_args()

    # Agregar paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)

    pipeline = PipelineMod2(
        scene_path=args.scene,
        output_dir=args.output,
        reset=args.reset,
        isotope=args.isotope,
        n_particles=int(args.n_particles),
        flip_rows=args.flip,
        flip_z=args.flip_z,
        refine_hu=args.refine_hu,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
