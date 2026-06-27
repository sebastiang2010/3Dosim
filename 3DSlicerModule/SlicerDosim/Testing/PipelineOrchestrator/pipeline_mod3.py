"""
PipelineMod3 - Modulo 3: Analisis Dosimetrico desde escena + MCTAL.
Flujo: carga escena .mrb, parsea MCTAL, convierte a Gy, DVH, MIRD,
reporte PDF, nodo de dosis 3D en Slicer.

REUTILIZA las funciones de run_dosimetry_from_scene.py (no duplica 1890 lines).

Sigue EXACTAMENTE el mismo patron que PipelineMod1 y PipelineMod2:
CheckpointManager, _checkpoint_step, _ai_review_paso, ConsolaComandos.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Optional

import numpy as np

from PipelineOrchestrator.checkpoint import CheckpointManager
from PipelineOrchestrator.worker import PipelineWorker
from PipelineOrchestrator.utils import logger as base_logger, add_module_path, show_progress
from PipelineOrchestrator.views import setup_medical_views, load_pipeline_config
from PipelineOrchestrator.comandos import ConsolaComandos
from PipelineOrchestrator import ai_supervisor

# ─── Reutilizar funciones de run_dosimetry_from_scene ────────────────────────
from PipelineOrchestrator.run_dosimetry_from_scene import (
    load_scene,
    find_nodes,
    compute_activity_from_pet,
    parse_mctal,
    convert_to_gy,
    compute_dvh,
    compute_biophysical,
    compute_mird,
    generate_pdf_report,
    _create_dvh_plots_slicer,
    # Constantes
    LIVER_INDEX,
    TUMOR_INDEX,
    PRETUMOR_INDEX,
    AIR_INDEX,
    ALPHA_BETA_LIVER,
    ALPHA_BETA_TUMOR,
    DENSIDAD_LIVER,
    DENSIDAD_TUMOR,
    DENSIDAD_PRETUMOR,
    DENSIDAD_BODY,
    DENSIDAD_AIR,
    Y90_HALF_LIFE_H,
    LAMDA_DECAY,
    MU_REPAIR,
    MEV2J,
    OUTPUT_DIR_DEFAULT,
    SCENE_DEFAULT,
    MCTAL_DEFAULT,
    LABELMAP_DEFAULT,
    AI_PIPE_DIR,
)
from PipelineOrchestrator.latex_report_generator import generate_latex_report

logger = logging.getLogger("3DosimMod3")

# ─── Constantes locales ──────────────────────────────────────────────────────

DEFAULT_NPS_LABEL = "1.0e+08"


# ======================================================================
# PipelineMod3
# ======================================================================

class PipelineMod3:
    """
    Pipeline Modulo 3: Analisis Dosimetrico desde escena + MCTAL.

    Pasos:
      1. Cargar escena .mrb
      2. Buscar CT, PET, Labelmap
      3. Computar actividad desde PET
      4. Parsear archivo MCTAL
      5. Convertir MeV/cm³ → Gy
      6. DVH y radiobiologia por estructura
      7. MIRD partition model
      8. Exportar reporte (JSON + TXT + PDF)
      9. Crear nodo de dosis 3D en Slicer + overlay
     10. Mostrar DVH en Slicer + guardar escena
    """

    STEP_LOAD_SCENE     = "load_scene"
    STEP_FIND_NODES     = "find_nodes"
    STEP_ACTIVITY       = "compute_activity"
    STEP_PARSE_MCTAL    = "parse_mctal"
    STEP_CONVERT        = "convert_to_gy"
    STEP_DVH            = "compute_dvh"
    STEP_MIRD           = "compute_mird"
    STEP_EXPORT_REPORT  = "export_report"
    STEP_DOSE_NODE      = "create_dose_node"
    STEP_DOSE_SCENE     = "dvh_and_save_scene"

    # ==================================================================
    # __init__
    # ==================================================================

    def __init__(
        self,
        scene_path: Optional[str] = None,
        mctal_path: Optional[str] = None,
        labelmap_path: Optional[str] = None,
        activity_gbq: Optional[float] = None,
        output_dir: Optional[str] = None,
        reset: bool = False,
        flip: bool = True,
        no_consola: bool = False,
        patient_id: Optional[str] = None,
    ):
        """
        Args:
            scene_path: Ruta a escena .mrb. Si None, auto-detecta.
            mctal_path: Ruta a archivo MCTAL. Si None, usa default.
            labelmap_path: Ruta a labelmap NIfTI. Si None, busca en escena.
            activity_gbq: Actividad en GBq. Si None, computa del PET.
            output_dir: Directorio de salida. Si None, usa default.
            reset: Reiniciar checkpoints.
            flip: Aplicar flip Y a dosis MCTAL (default True).
            no_consola: Deshabilitar consola interactiva.
        """
        # ── Paths ──
        self.scene_path = scene_path or self._auto_detect_scene()
        self.mctal_path = mctal_path or MCTAL_DEFAULT
        self.labelmap_path = labelmap_path or LABELMAP_DEFAULT
        self.activity_gbq_input = activity_gbq
        self.flip = flip

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = OUTPUT_DIR_DEFAULT

        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints", "mod3")
        self.results_data = {
            "metadata": {},
            "structures": {},
            "mird": {},
        }

        self.patient_id = patient_id
        self.checkpoint = CheckpointManager(self.checkpoint_dir)
        if reset:
            self.checkpoint.reset()

        # ── Nodos Slicer (se llenan en load/find nodes) ──
        self.ct_node = None
        self.pet_node = None
        self.labelmap_node = None
        self.segmentation_node = None
        self.dose_node = None

        # ── Arrays (se llenan durante el pipeline) ──
        self.labelmap_array: Optional[np.ndarray] = None
        self.dose_mev_cm3: Optional[np.ndarray] = None
        self.dose_gy: Optional[np.ndarray] = None
        self.error_3d: Optional[np.ndarray] = None
        self.activity_bq: float = 0.0
        self.activity_gbq: float = 0.0
        self.dims: tuple = ()
        self.spacing: tuple = ()
        self.dvh_curves_for_pdf: list = []
        self.pdf_path: Optional[str] = None

        # ── Resultados para checkpoint ──
        self.results = {"pasos": [], "errores": [], "tiempos": {}}

        # ── Consola ──
        self.no_consola = no_consola
        self.consola = None
        if not no_consola:
            try:
                self.consola = ConsolaComandos(output_dir=self.output_dir)
            except Exception:
                self.consola = None

        # ── Config ──
        self.pipeline_config = load_pipeline_config()
        self.scene_output_dir = self.pipeline_config.get(
            "scene_output_dir",
            os.path.join(self.output_dir, "scenes"),
        )

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Modulo 3 — Analisis Dosimetrico")
        logger.info("=" * 60)
        logger.info(f"  Escena:       {self.scene_path or 'NO DISPONIBLE'}")
        logger.info(f"  MCTAL:        {self.mctal_path}")
        logger.info(f"  Labelmap:     {self.labelmap_path}")
        logger.info(f"  Activity:     {activity_gbq if activity_gbq is not None else 'desde PET'} GBq")
        logger.info(f"  Flip Y:       {flip}")
        logger.info(f"  Output:       {self.output_dir}")
        logger.info(f"  Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"  Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info(f"  Consola:      {'SI' if not no_consola else 'NO'}")
        logger.info("")

    # ==================================================================
    # RUN (blocking — backward compatible)
    # ==================================================================

    def run(self):
        """Ejecuta el pipeline Mod3 de forma BLOQUEANTE.

        Usa PipelineWorker internamente pero se bloquea hasta que
        todos los pasos terminen. Compatible con entry points existentes.
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 3")
        logger.info("")

        if self.consola:
            self.consola.log("=" * 50)
            self.consola.log(" 3Dosim Mod3 - Analisis Dosimetrico")
            self.consola.log(" Escribi 'ayuda' para comandos disponibles")
            self.consola.log("=" * 50)
            self.consola.log("")
            self.consola.mostrar()
        self._log_consola("Iniciando Modulo 3...")

        # ── Verificar pre-requisitos ──
        if not self.scene_path or not os.path.exists(self.scene_path):
            logger.error(f"Escena .mrb no encontrada: {self.scene_path}")
            logger.error("Ejecute Modulo 1 primero o especifique --scene")
            self._log_consola_error("ERROR: Escena .mrb no encontrada")
            self._report()
            return

        if not os.path.exists(self.mctal_path):
            logger.error(f"Archivo MCTAL no encontrado: {self.mctal_path}")
            logger.error("Ejecute MCNP primero o especifique --mctal")
            self._log_consola_error("ERROR: Archivo MCTAL no encontrado")
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
            self._log_consola("Modulo 3 finalizado EXITOSAMENTE")
        else:
            self._log_consola("Modulo 3 finalizado con ERRORES. Revise el reporte.")

    # ────────────────────────────────────────────────────────────
    # RUN ASYNC (non-blocking)
    # ────────────────────────────────────────────────────────────

    def run_async(self, on_completed=None, on_error=None):
        """
        Ejecuta el pipeline Mod3 de forma NO BLOQUEANTE.

        Args:
            on_completed: callback(success: bool)
            on_error: callback(step_name: str, error: str)
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 3 (async)")
        logger.info("")

        if self.consola:
            self.consola.log("=" * 50)
            self.consola.log(" 3Dosim Mod3 - Analisis Dosimetrico")
            self.consola.log(" Escribi 'ayuda' para comandos disponibles")
            self.consola.log("=" * 50)
            self.consola.log("")
            self.consola.mostrar()
        self._log_consola("Iniciando Modulo 3...")

        if not self.scene_path or not os.path.exists(self.scene_path):
            logger.error(f"Escena .mrb no encontrada: {self.scene_path}")
            if on_error:
                on_error("escena", f"Escena no encontrada: {self.scene_path}")
            return

        if not os.path.exists(self.mctal_path):
            logger.error(f"Archivo MCTAL no encontrado: {self.mctal_path}")
            if on_error:
                on_error("mctal", f"MCTAL no encontrado: {self.mctal_path}")
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

        logger.info("  [Async] Pipeline Mod3 iniciado — Slicer responde durante la ejecucion")

    # ────────────────────────────────────────────────────────────
    # BUILD WORKER
    # ────────────────────────────────────────────────────────────

    def _build_worker(self):
        """Construye el PipelineWorker con los pasos de Mod3."""
        steps = []

        # Paso 1: check_slicer
        steps.append(("check_slicer", False,
                      lambda: self._always_run_step(
                          "check_slicer", "Verificando entorno Slicer",
                          self._check_slicer, critical=True,
                          post_fn=add_module_path)))

        # Paso 2: load_scene (SIEMPRE se ejecuta)
        steps.append(("load_scene", False,
                      lambda: self._always_run_step(
                          "load_scene", "Cargando escena .mrb",
                          self._load_scene, critical=True,
                          post_fn=lambda: self._log_consola_ok("Escena cargada exitosamente"))))

        # Paso 3: find_nodes (SIEMPRE se ejecuta)
        steps.append(("find_nodes", False,
                      lambda: self._always_run_step(
                          "find_nodes", "Buscando nodos (CT, PET, Labelmap)",
                          self._find_and_prepare_nodes, critical=True,
                          post_fn=lambda: self._log_consola_ok(
                              f"Nodos: CT={self.ct_node.GetName() if self.ct_node else 'N/A'}, "
                              f"PET={self.pet_node.GetName() if self.pet_node else 'N/A'}, "
                              f"Labelmap={self.labelmap_node.GetName() if self.labelmap_node else 'N/A'}"))))

        # Paso 4: compute_activity (light)
        steps.append((self.STEP_ACTIVITY, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_ACTIVITY, "Actividad desde PET",
                          self._compute_activity,
                          data_func=lambda: {
                              "activity_bq": self.activity_bq,
                              "activity_gbq": self.activity_gbq,
                              "method": "from_PET" if self.activity_gbq_input is None else "input",
                          },
                          post_fn=lambda: self._post_activity())))

        # Paso 5: parse_mctal (~30s → HEAVY)
        steps.append((self.STEP_PARSE_MCTAL, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_PARSE_MCTAL, "Parsear MCTAL",
                          self._parse_mctal,
                          critical=True,
                          data_func=lambda: {
                              "mctal_path": self.mctal_path,
                              "dims": list(self.dims),
                              "nps": int(getattr(self, '_mctal_nps', 0)),
                          },
                          post_fn=lambda: self._post_mctal())))

        # Paso 6: convert_to_gy (light)
        steps.append((self.STEP_CONVERT, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_CONVERT, "Convertir a Gy",
                          self._convert_to_gy,
                          critical=True,
                          data_func=lambda: {
                              "mean_dose": float(np.mean(self.dose_gy[self.dose_gy > 0])) if self.dose_gy is not None and np.any(self.dose_gy > 0) else 0,
                              "max_dose": float(np.max(self.dose_gy)) if self.dose_gy is not None else 0,
                              "bad_voxels_removed": int(getattr(self, '_n_bad_voxels', 0)),
                              "neg_voxels_zeroed": int(getattr(self, '_n_neg_voxels', 0)),
                          },
                          post_fn=lambda: self._tomar_screenshot("03_dosis_gy"))))

        # Paso 7: compute_dvh (light)
        steps.append((self.STEP_DVH, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_DVH, "DVH y radiobiologia",
                          self._compute_dvh,
                          data_func=lambda: {
                              "structures": {
                                  name: {
                                      "n_voxels": s.get("n_voxels", 0),
                                      "mean_dose_gy": s.get("mean_dose_gy", 0),
                                      "d98_gy": s.get("d98_gy", 0),
                                      "bed_gy": s.get("bed_gy", 0),
                                  }
                                  for name, s in self.results_data.get("structures", {}).items()
                              },
                          },
                          post_fn=lambda: self._post_dvh())))

        # Paso 8: compute_mird (light)
        steps.append((self.STEP_MIRD, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_MIRD, "MIRD partition model",
                          self._compute_mird,
                          data_func=lambda: {"mird": self.results_data.get("mird", {})},
                          post_fn=lambda: self._tomar_screenshot("05_mird"))))

        # Paso 9: export_report (PDF ~30-60s → HEAVY)
        steps.append((self.STEP_EXPORT_REPORT, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_EXPORT_REPORT, "Exportar reporte",
                          self._export_report,
                          data_func=lambda: {
                              "json_path": getattr(self, '_report_json_path', ""),
                              "txt_path": getattr(self, '_report_txt_path', ""),
                              "pdf_path": self.pdf_path or "",
                          },
                          post_fn=lambda: self._post_report())))

        # Paso 10: create_dose_node (light)
        steps.append((self.STEP_DOSE_NODE, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_DOSE_NODE, "Nodo de dosis 3D",
                          self._create_dose_node,
                          data_func=lambda: {
                              "dose_node_name": self.dose_node.GetName() if self.dose_node else None,
                          },
                          post_fn=lambda: self._post_dose_node())))

        # Paso 11: dvh_and_save_scene (light)
        steps.append((self.STEP_DOSE_SCENE, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_DOSE_SCENE, "DVH en Slicer + escena final",
                          self._create_dvh_and_save,
                          data_func=lambda: {
                              "scene_saved": os.path.exists(os.path.join(self.output_dir, "3Dosim_dosis_scene.mrb")),
                          },
                          post_fn=lambda: self._tomar_screenshot("10_dvh_final"))))

        self.worker = PipelineWorker(steps)

        # ── Conectar señales ──
        self.worker.step_completed.connect(self._on_worker_step_completed)
        self.worker.step_error.connect(self._on_worker_step_error)
        self.worker.blocking_started.connect(self._on_worker_blocking_started)
        self.worker.pipeline_completed.connect(self._on_worker_pipeline_completed)

    # ────────────────────────────────────────────────────────────
    # POST-STEP HANDLERS (acciones por paso)
    # ────────────────────────────────────────────────────────────

    def _post_activity(self):
        self._save_scene("01_post_activity")
        self._tomar_screenshot("01_actividad")

    def _post_mctal(self):
        self._save_scene("02_post_mctal")
        self._tomar_screenshot("02_mctal_parseado")

    def _post_dvh(self):
        self._save_scene("03_post_dvh")
        self._tomar_screenshot("04_dvh")

    def _post_report(self):
        self._save_scene("04_post_report")
        self._tomar_screenshot("06_reporte")

    def _post_dose_node(self):
        self._save_scene("05_post_dose_node")
        self._tomar_screenshot("07_dosis_3d")

    # ────────────────────────────────────────────────────────────
    # WORKER SIGNAL HANDLERS
    # ────────────────────────────────────────────────────────────

    def _on_worker_step_completed(self, name, result, elapsed):
        logger.info(f"  [Worker] Paso '{name}' OK ({elapsed:.1f}s)")

    def _on_worker_step_error(self, name, error_msg, elapsed):
        logger.error(f"  [Worker] Paso '{name}' FALLO: {error_msg}")

    def _on_worker_blocking_started(self, name):
        self._log_consola(f"Iniciando paso pesado: {name} (Slicer responde en paralelo)...")

    def _on_worker_pipeline_completed(self):
        """Todos los pasos terminaron."""
        errores = self.results.get("errores", [])
        has_fatal = any("CRITICO" in e for e in errores)

        logger.info("")
        logger.info("  PIPELINE MODULO 3 COMPLETADO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. Cargar escena .mrb")
        logger.info("    2. Buscar nodos (CT, PET, Labelmap)")
        logger.info("    3. Computar actividad desde PET")
        logger.info("    4. Parsear archivo MCTAL")
        logger.info("    5. Convertir MeV/cm3 a Gy")
        logger.info("    6. DVH y radiobiologia por estructura")
        logger.info("    7. MIRD partition model")
        logger.info("    8. Exportar reporte (JSON + TXT + PDF)")
        logger.info("    9. Crear nodo de dosis 3D en Slicer")
        logger.info("   10. Graficar DVH en Slicer + guardar escena")
        logger.info("")

        self._log_consola("Modulo 3 completado. Generando reporte...")
        ok = not has_fatal
        self._report()

    # ────────────────────────────────────────────────────────────
    # WRAPPER: checkpoint_step unificado
    # ────────────────────────────────────────────────────────────

    def _checkpoint_step_wrapper(self, step_name, display_name, func,
                                  data_func=None, critical=False, post_fn=None):
        """Wrapper unificado con checkpoint, timing, registro y post-action."""
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            self._log_consola(f"[checkpoint] {display_name} — ya completado, saltando")
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
        self._log_consola(f"Ejecutando: {display_name}...")

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
            self._log_consola_ok(f"{display_name} — {elapsed:.1f}s")
            self._ai_review_paso(display_name, ok=True, elapsed=elapsed,
                                 step_name=step_name, data=data)

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
            self._log_consola_error(f"{display_name} — FALLO: {e}")
            self._ai_review_paso(display_name, ok=False, elapsed=elapsed,
                                 step_name=step_name, error=str(e))
            if critical:
                logger.error(f"  [CRITICO] {display_name} fallo — abortando")
                self.worker.abort()
            return False

    def _always_run_step(self, name, display_name, func, critical=False, post_fn=None):
        """
        Ejecuta un paso que SIEMPRE corre (no checkpointeable).
        Registra el resultado en self.results["pasos"].
        """
        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        show_progress(f"Ejecutando: {display_name}")
        self._log_consola(f"Ejecutando: {display_name}...")
        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed
            })
            show_progress(f"{display_name} completado")
            self._log_consola_ok(f"{display_name} — {elapsed:.1f}s")
            if post_fn:
                try:
                    post_fn()
                except Exception as e:
                    logger.debug(f"Post-step fallo: {e}")
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
            self._log_consola_error(f"{display_name} — FALLO: {e}")
            if critical:
                self.worker.abort()
            raise  # re-raise to let worker handle signal emission

    def _check_slicer(self):
        """Verifica que estamos dentro de 3D Slicer."""
        try:
            import slicer
            version = f"{slicer.app.majorVersion}.{slicer.app.minorVersion}"
            logger.info(f"  Slicer version: {version}")
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    # ==================================================================
    # CHECKPOINT + HELPERS (mismo patron que PipelineMod1)
    # ==================================================================

    def _checkpoint_step(self, step_name, display_name, func, data_func=None):
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True,
            })
            self._log_consola(f"[checkpoint] {display_name} — ya completado, saltando")
            cp_data = self.checkpoint.get_data(step_name)
            if cp_data:
                self._restore_step_state(step_name, cp_data)
            return True

        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        show_progress(f"Ejecutando: {display_name}")
        self._log_consola(f"Ejecutando: {display_name}...")

        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed,
            })
            self.results["tiempos"][display_name] = elapsed
            data = data_func() if data_func else {}
            self.checkpoint.mark_completed(step_name, data=data)
            show_progress(f"{display_name} completado")
            self._log_consola_ok(f"{display_name} — {elapsed:.1f}s")
            self._ai_review_paso(display_name, ok=True, elapsed=elapsed,
                                 step_name=step_name, data=data)
            return True
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  FALLO: {e}")
            self.results["pasos"].append({
                "nombre": display_name, "ok": False, "tiempo": elapsed,
            })
            self.results["errores"].append(f"{display_name}: {e}")
            show_progress(f"FALLO: {display_name}")
            self._log_consola_error(f"{display_name} — FALLO: {e}")
            self._ai_review_paso(display_name, ok=False, elapsed=elapsed,
                                 step_name=step_name, error=str(e))
            return False

    def _ai_review_paso(self, display_name, ok, elapsed, step_name, data=None, error=None):
        """Revisa el paso via AI supervisor (DeepSeek/OpenRouter)."""
        try:
            ctx = {
                "paso": display_name,
                "ok": ok,
                "tiempo": elapsed,
                "datos": data or {},
                "errores": [error] if error else [],
            }
            nodos_info = {}
            if self.ct_node:
                nodos_info["CT"] = self.ct_node.GetName()
            if self.pet_node:
                nodos_info["PET"] = self.pet_node.GetName()
            if self.labelmap_node:
                nodos_info["Labelmap"] = self.labelmap_node.GetName()
            if self.dose_node:
                nodos_info["Dosis"] = self.dose_node.GetName()
            ctx["datos"]["nodos_activos"] = nodos_info
            ctx["datos"]["activity_gbq"] = self.activity_gbq
            if self.dose_gy is not None:
                ctx["datos"]["dose_max_gy"] = float(np.max(self.dose_gy))
                ctx["datos"]["dose_mean_gt0_gy"] = float(np.mean(self.dose_gy[self.dose_gy > 0])) if np.any(self.dose_gy > 0) else 0
            ai_supervisor.revisar_paso(ctx, consola=self.consola)
        except Exception as e:
            logger.debug(f"AI review no disponible: {e}")

    def _restore_step_state(self, step_name, data):
        """Restaura estado desde checkpoint data."""
        if not data:
            return
        import slicer

        # Restaurar nodos por nombre
        node_keys = {
            "ct_node": "ct_node",
            "pet_node": "pet_node",
            "labelmap_node": "labelmap_node",
            "dose_node": "dose_node",
        }
        for data_key, attr_name in node_keys.items():
            name_key = data_key + "_name"
            node_name = None
            if name_key in data and data[name_key]:
                node_name = data[name_key]
            elif data_key in data and isinstance(data[data_key], str) and data[data_key]:
                node_name = data[data_key]
            if node_name:
                try:
                    node = slicer.util.getNode(node_name)
                    setattr(self, attr_name, node)
                except Exception:
                    pass

        # Restaurar valores escalares
        scalar_map = {
            "activity_bq": "activity_bq",
            "activity_gbq": "activity_gbq",
            "dims": "dims",
            "spacing": "spacing",
        }
        for data_key, attr_name in scalar_map.items():
            if data_key in data and data[data_key] is not None:
                setattr(self, attr_name, data[data_key])

        # Restaurar arrays desde paths guardados
        if data.get("dose_gy_path") and os.path.exists(data["dose_gy_path"]):
            try:
                self.dose_gy = np.load(data["dose_gy_path"])
            except Exception:
                pass
        if data.get("labelmap_path_saved") and os.path.exists(data["labelmap_path_saved"]):
            try:
                self.labelmap_array = np.load(data["labelmap_path_saved"])
            except Exception:
                pass

        # Restaurar resultados_data
        if data.get("results_data"):
            self.results_data = data["results_data"]

        # Restaurar PDF path
        if data.get("pdf_path"):
            self.pdf_path = data["pdf_path"]

        # Restaurar visualizacion si hay nodos
        if self.ct_node or self.pet_node:
            try:
                setup_medical_views(
                    ct_node=self.ct_node,
                    pet_node=self.pet_node,
                )
            except Exception as e:
                logger.debug(f"No se pudo restaurar visualizacion: {e}")

    def _save_scene(self, tag=None):
        """Guarda escena .mrb actual (una sola, se sobrescribe)."""
        try:
            import slicer
            filename = "3Dosim_mod3_scene.mrb"
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

    def _tomar_screenshot(self, nombre):
        """Toma screenshot de toda la ventana de Slicer."""
        try:
            import slicer
            from datetime import datetime
            ts = datetime.now().strftime("%H%M%S")
            shot_dir = os.path.join(self.output_dir, "screenshots")
            os.makedirs(shot_dir, exist_ok=True)
            filepath = os.path.join(shot_dir, f"{ts}_{nombre}.png")
            mw = slicer.util.mainWindow()
            if mw:
                pixmap = mw.grab()
                pixmap.save(filepath)
                logger.info(f"  Screenshot: {os.path.basename(filepath)}")
                return filepath
        except Exception as e:
            logger.warning(f"No se pudo tomar screenshot '{nombre}': {e}")
            return None

    def _save_results_json(self):
        """Guarda resultados en JSON (historial acumulado)."""
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
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modulo": "Mod3",
            "scene_path": self.scene_path,
            "mctal_path": self.mctal_path,
            "activity_gbq": self.activity_gbq,
            "output_dir": self.output_dir,
            "flip": self.flip,
            "total_pasos": total,
            "exitosos": ok_count,
            "fallos": fails,
            "resultado": "OK" if fails == 0 else "ERROR",
            "pasos": self.results["pasos"],
            "errores": self.results["errores"],
            "estructuras": {
                name: {
                    "mean_dose_gy": s.get("mean_dose_gy", 0),
                    "bed_gy": s.get("bed_gy", 0),
                }
                for name, s in self.results_data.get("structures", {}).items()
            },
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
        logger.info(" REPORTE FINAL - MODULO 3")
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
        logger.info("")
        if self.results_data.get("structures"):
            logger.info("  DOSIMETRIA POR ESTRUCTURA:")
            for name, s in self.results_data["structures"].items():
                logger.info(f"    {name}: Dmedia={s.get('mean_dose_gy', 0):.2f} Gy, "
                           f"BED={s.get('bed_gy', 0):.2f} Gy")
        logger.info(f"  Output: {self.output_dir}")
        if self.pdf_path:
            logger.info(f"  PDF:    {self.pdf_path}")
        all_ok = fails == 0
        if all_ok:
            logger.info("  RESULTADO: TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f"  RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)
        return all_ok

    # ==================================================================
    # LOGGING A CONSOLA
    # ==================================================================

    def _log_consola(self, mensaje: str):
        if self.consola:
            self.consola.log(mensaje)

    def _log_consola_ok(self, mensaje: str):
        if self.consola:
            self.consola.log_ok(mensaje)

    def _log_consola_error(self, mensaje: str):
        if self.consola:
            self.consola.log_error(mensaje)

    # ==================================================================
    # STEP METHODS
    # ==================================================================

    # ── 1. Cargar escena ──

    def _load_scene(self):
        """Carga escena .mrb en Slicer."""
        import slicer

        if not os.path.exists(self.scene_path):
            raise FileNotFoundError(f"Escena no encontrada: {self.scene_path}")

        size_mb = os.path.getsize(self.scene_path) / (1024 * 1024)
        logger.info(f"  Escena: {self.scene_path} ({size_mb:.0f} MB)")

        success = load_scene(self.scene_path)
        if not success:
            raise RuntimeError(f"No se pudo cargar escena: {self.scene_path}")

        logger.info("  Escena cargada exitosamente")

    # ── 2. Buscar nodos ──

    def _find_and_prepare_nodes(self):
        """Busca CT, PET, Labelmap en la escena cargada."""
        import slicer

        nodes = find_nodes(labelmap_name="3Dosim_labelmap")

        if nodes.get("ct"):
            self.ct_node = nodes["ct"]
            logger.info(f"  CT: '{self.ct_node.GetName()}'")
        else:
            raise RuntimeError("No se encontro nodo CT en la escena")

        if nodes.get("pet"):
            self.pet_node = nodes["pet"]
            logger.info(f"  PET: '{self.pet_node.GetName()}'")
        else:
            self.pet_node = None
            logger.info("  PET: No encontrado (se requiere --activity)")

        # Labelmap: primero buscar en escena, luego en NIfTI
        labelmap_from_scene = nodes.get("labelmap")
        if labelmap_from_scene:
            self.labelmap_node = labelmap_from_scene
            logger.info(f"  Labelmap: '{self.labelmap_node.GetName()}' (desde escena)")
        elif os.path.exists(self.labelmap_path):
            logger.info(f"  Cargando labelmap desde NIfTI: {self.labelmap_path}")
            labelmap_node = slicer.util.loadVolume(self.labelmap_path)
            if labelmap_node:
                self.labelmap_node = labelmap_node
                logger.info(f"  Labelmap: '{self.labelmap_node.GetName()}' (desde NIfTI)")
            else:
                raise RuntimeError(f"No se pudo cargar labelmap NIfTI: {self.labelmap_path}")
        else:
            # Buscar segmentacion como fallback
            seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
            if seg_nodes:
                self.segmentation_node = seg_nodes[0]
                logger.info(f"  Segmentacion: '{self.segmentation_node.GetName()}' (fallback)")
                # No hay labelmap array disponible, continuar con datos limitados
                logger.warning("  No hay labelmap numerico. MIRD y DVH no estaran disponibles.")
            else:
                raise RuntimeError("No se encontro labelmap ni segmentacion")

        # Extraer labelmap array
        if self.labelmap_node:
            self.labelmap_array = self._get_labelmap_array(self.labelmap_node)
            self.dims = self.labelmap_array.shape  # (nx, ny, nz)
            self.spacing = self.labelmap_node.GetSpacing()
            logger.info(f"  Labelmap shape: {self.dims}")
            logger.info(f"  Spacing: {self.spacing}")
            logger.info(f"  Indices unicos: {np.unique(self.labelmap_array)}")
        else:
            # Sin labelmap: usar dimensiones del CT
            if self.ct_node:
                img = self.ct_node.GetImageData()
                if img:
                    self.dims = (img.GetDimensions()[0], img.GetDimensions()[1], img.GetDimensions()[2])
                else:
                    self.dims = (512, 512, 171)
            self.spacing = (1.0, 1.0, 1.0)

    @staticmethod
    def _get_labelmap_array(labelmap_node):
        """Extrae array 3D del labelmap, transpone a (nx, ny, nz)."""
        import slicer
        arr = slicer.util.arrayFromVolume(labelmap_node)  # (nz, ny, nx)
        arr = arr.transpose(2, 1, 0).astype(np.int32)    # (nx, ny, nz)
        return arr

    # ── 3. Actividad ──

    def _compute_activity(self):
        """Computa actividad total desde PET o usa valor ingresado."""
        if self.activity_gbq_input is not None:
            self.activity_gbq = float(self.activity_gbq_input)
            self.activity_bq = self.activity_gbq * 1e9
            logger.info(f"  Actividad (input): {self.activity_gbq:.4f} GBq")
            return

        if self.pet_node is None:
            raise RuntimeError("No hay PET y no se especifico --activity")

        activity_bq = compute_activity_from_pet(self.pet_node)
        self.activity_bq = float(activity_bq)
        self.activity_gbq = self.activity_bq / 1e9

        logger.info(f"  Actividad: {self.activity_bq:.2e} Bq = {self.activity_gbq:.4f} GBq")

    # ── 4. Parsear MCTAL ──

    def _parse_mctal(self):
        """Parsea archivo MCTAL usando MCTALParser."""
        if not os.path.exists(self.mctal_path):
            raise FileNotFoundError(f"MCTAL no encontrado: {self.mctal_path}")

        size_mb = os.path.getsize(self.mctal_path) / (1024 * 1024)
        logger.info(f"  MCTAL: {self.mctal_path} ({size_mb:.0f} MB)")

        nx, ny, nz = self.dims
        mctal_result = parse_mctal(self.mctal_path, (nx, ny, nz))

        self.dose_mev_cm3 = mctal_result["dose_3d"]
        self.error_3d = mctal_result.get("uncertainty", np.zeros_like(self.dose_mev_cm3))
        self._mctal_nps = mctal_result.get("nps", 0)

        logger.info(f"  Dose shape: {self.dose_mev_cm3.shape}")
        logger.info(f"  NPS: {self._mctal_nps:,}")

        # Aplicar flip Y si corresponde (compatibilidad MATLAB)
        if self.flip:
            self.dose_mev_cm3 = self.dose_mev_cm3[:, ::-1, :].copy()
            self.error_3d = self.error_3d[:, ::-1, :].copy()
            logger.info("  Flip Y aplicado a dosis MCTAL")

    # ── 5. Convertir a Gy ──

    def _convert_to_gy(self):
        """Convierte MeV/cm3/particula a Gy."""
        if self.dose_mev_cm3 is None:
            raise RuntimeError("No hay datos de dosis MCTAL para convertir")

        t_meanlife_s = Y90_HALF_LIFE_H * 3600 / np.log(2)  # ~332,753 s

        if self.labelmap_array is not None:
            self.dose_gy = convert_to_gy(
                self.dose_mev_cm3, self.labelmap_array,
                self.activity_bq, t_meanlife_s,
            )
        else:
            # Sin labelmap: densidad uniforme
            self.dose_gy = self.dose_mev_cm3 * MEV2J * t_meanlife_s * self.activity_bq * 1000

        # Aplicar filtro de error (MATLAB cargo_mctal.m:375-379)
        error_eliminar = 1.5
        bad_voxels = self.error_3d >= error_eliminar
        self.dose_gy[bad_voxels] = 0
        self._n_bad_voxels = int(np.sum(bad_voxels))

        # Eliminar dosis negativas
        neg_mask = self.dose_gy < 0
        self._n_neg_voxels = int(np.sum(neg_mask))
        self.dose_gy[neg_mask] = 0

        # Estadisticas
        positive = self.dose_gy > 0
        n_pos = int(np.sum(positive))
        logger.info(f"  Voxels eliminados por error>={error_eliminar}: {self._n_bad_voxels}")
        logger.info(f"  Voxels con dosis negativa: {self._n_neg_voxels}")
        logger.info(f"  Dosis en Gy: media={np.mean(self.dose_gy[positive]) if np.any(positive) else 0:.2f}, "
                    f"max={np.max(self.dose_gy):.2f}, n_pos={n_pos}")

    # ── 6. DVH por estructura ──

    def _compute_dvh(self):
        """Computa DVH y radiobiologia para higado, tumor, pretumor."""
        if self.dose_gy is None or self.labelmap_array is None:
            raise RuntimeError("Dosis Gy o labelmap no disponibles para DVH")

        structures_def = {
            "higado": {"idx": LIVER_INDEX, "alpha_beta": ALPHA_BETA_LIVER, "is_tumor": False},
            "tumor": {"idx": TUMOR_INDEX, "alpha_beta": ALPHA_BETA_TUMOR, "is_tumor": True},
            "pretumor": {"idx": PRETUMOR_INDEX, "alpha_beta": ALPHA_BETA_LIVER, "is_tumor": False},
        }

        spacing = self.spacing
        struct_labels_pdf = {"higado": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}
        dvh_colors_pdf = {
            "higado": (0.2, 0.4, 1.0),
            "tumor": (1.0, 0.2, 0.2),
            "pretumor": (0.8, 0.6, 0.0),
        }

        self.results_data["structures"] = {}
        self.dvh_curves_for_pdf = []

        for name, info in structures_def.items():
            idx = info["idx"]
            mask = self.labelmap_array == idx
            n_vox = int(np.sum(mask))

            if n_vox == 0:
                logger.info(f"  {name} ({idx}): sin voxeles, saltando")
                continue

            # DVH
            dvh = compute_dvh(self.dose_gy, self.labelmap_array, idx)
            logger.info(f"  {name} ({idx}): {dvh['n_voxels']} voxels, "
                        f"Dmedia={dvh['mean_dose_gy']:.2f} Gy")

            # Radiobiologia
            bio = compute_biophysical(dvh, info["alpha_beta"], info["is_tumor"])
            logger.info(f"    BED={bio['bed_gy']:.2f} Gy, EUD={bio['eud_gy']:.2f} Gy")

            volume_cm3 = n_vox * spacing[0] * spacing[1] * spacing[2] / 1000.0

            self.results_data["structures"][name] = {
                "index": idx,
                "n_voxels": dvh["n_voxels"],
                "volume_cm3": volume_cm3,
                "mean_dose_gy": dvh["mean_dose_gy"],
                "min_dose_gy": dvh["min_dose_gy"],
                "max_dose_gy": dvh["max_dose_gy"],
                "std_dose_gy": dvh["std_dose_gy"],
                "d98_gy": dvh["d98_gy"],
                "d70_gy": dvh["d70_gy"],
                "d50_gy": dvh["d50_gy"],
                "bed_gy": bio["bed_gy"],
                "eud_gy": bio["eud_gy"],
                "eqd2_gy": bio["eqd2_gy"],
            }

            # Curva DVH para PDF
            doses = self.dose_gy[mask]
            n_doses = len(doses)
            if n_doses > 0 and np.max(doses) > 0:
                Dmax = float(np.max(doses))
                delta = Dmax / 1000.0
                d_vals = np.arange(0, Dmax + delta, delta)
                a_vals = np.zeros(len(d_vals))
                for i, d in enumerate(d_vals):
                    a_vals[i] = np.sum(doses >= d) * 100.0 / n_doses
                pdf_label = struct_labels_pdf.get(name, name)
                self.dvh_curves_for_pdf.append((pdf_label, d_vals, a_vals))

    # ── 7. MIRD ──

    def _compute_mird(self):
        """Calcula MIRD partition model."""
        if self.dose_gy is None or self.labelmap_array is None:
            raise RuntimeError("Dosis Gy o labelmap no disponibles para MIRD")

        mird = compute_mird(self.dose_gy, self.labelmap_array, self.activity_gbq)
        self.results_data["mird"] = mird

        logger.info(f"  Hígado:       {mird['liver']['mean_dose_gy']:.2f} Gy")
        logger.info(f"  Tumor:        {mird['tumor']['mean_dose_gy']:.2f} Gy")
        logger.info(f"  Peritumoral:  {mird['pretumor']['mean_dose_gy']:.2f} Gy")

    # ── 8. Exportar reporte ──

    def _export_report(self):
        """Exporta reporte JSON + TXT + PDF."""
        # Metadata
        self.results_data["metadata"] = {
            "scene": self.scene_path,
            "mctal": self.mctal_path,
            "activity_bq": self.activity_bq,
            "activity_gbq": self.activity_gbq,
            "dimensions": list(self.dims),
            "nps": int(getattr(self, '_mctal_nps', 0)),
            "flip": self.flip,
        }

        # JSON
        report_path = os.path.join(self.output_dir, "dosimetria_report.json")
        with open(report_path, "w") as f:
            json.dump(self.results_data, f, indent=2, default=str)
        self._report_json_path = report_path
        logger.info(f"  Reporte JSON: {report_path}")

        # TXT
        report_txt_path = os.path.join(self.output_dir, "dosimetria_report.txt")
        with open(report_txt_path, "w") as f:
            f.write("=" * 60 + "\n")
            f.write(" REPORTE DE DOSIMETRIA 3Dosim\n")
            f.write("=" * 60 + "\n\n")
            meta = self.results_data.get("metadata", {})
            f.write(f"Escena:    {meta.get('scene', 'N/A')}\n")
            f.write(f"MCTAL:     {meta.get('mctal', 'N/A')}\n")
            f.write(f"Actividad: {meta.get('activity_gbq', 0):.4f} GBq\n")
            f.write(f"NPS:       {meta.get('nps', 0):,}\n")
            f.write(f"Dimensiones: {meta.get('dimensions', [])}\n\n")

            f.write("-" * 50 + "\n")
            f.write(" RESULTADOS POR ESTRUCTURA\n")
            f.write("-" * 50 + "\n\n")
            for name, s in self.results_data.get("structures", {}).items():
                f.write(f"  {name.upper()} (indice={s['index']}):\n")
                f.write(f"    Voxeles:     {s['n_voxels']}\n")
                f.write(f"    Dosis media: {s['mean_dose_gy']:.2f} Gy\n")
                f.write(f"    D98:         {s['d98_gy']:.2f} Gy\n")
                f.write(f"    D70:         {s['d70_gy']:.2f} Gy\n")
                f.write(f"    D50:         {s['d50_gy']:.2f} Gy\n")
                f.write(f"    BED:         {s['bed_gy']:.2f} Gy\n")
                f.write(f"    EUD:         {s['eud_gy']:.2f} Gy\n")
                f.write(f"    EQD2:        {s['eqd2_gy']:.2f} Gy\n\n")

            f.write("-" * 50 + "\n")
            f.write(" MIRD PARTITION MODEL\n")
            f.write("-" * 50 + "\n\n")
            mird = self.results_data.get("mird", {})
            f.write(f"  Actividad: {meta.get('activity_gbq', 0):.4f} GBq\n")
            f.write(f"  Higado:    {mird.get('liver', {}).get('mean_dose_gy', 0):.2f} Gy\n")
            f.write(f"  Tumor:     {mird.get('tumor', {}).get('mean_dose_gy', 0):.2f} Gy\n")
            f.write(f"  Peritumoral: {mird.get('pretumor', {}).get('mean_dose_gy', 0):.2f} Gy\n")
        self._report_txt_path = report_txt_path
        logger.info(f"  Reporte TXT: {report_txt_path}")

        # PDF (reportlab)
        try:
            pdf_path = generate_pdf_report(
                self.results_data,
                AI_PIPE_DIR,
                self.dvh_curves_for_pdf,
            )
            if pdf_path:
                self.pdf_path = pdf_path
                logger.info(f"  Reporte PDF: {pdf_path}")
            else:
                logger.warning("  generate_pdf_report devolvio None")
        except Exception as e:
            logger.warning(f"  Error generando PDF: {e}")
            import traceback
            logger.warning(traceback.format_exc())

        # PDF (LaTeX)
        try:
            latex_pdf = generate_latex_report(
                self.results_data,
                self.output_dir,
                patient_id=self.patient_id or "",
                dvh_curves=self.dvh_curves_for_pdf,
            )
            if latex_pdf:
                logger.info(f"  Reporte LaTeX: {latex_pdf}")
            else:
                logger.warning("  generate_latex_report devolvio None")
        except Exception as e:
            logger.warning(f"  Error generando reporte LaTeX: {e}")
            import traceback
            logger.warning(traceback.format_exc())

    # ── 9. Nodo de dosis 3D ──

    def _create_dose_node(self):
        """Crea nodo de dosis 3D en Slicer y activa overlay."""
        import slicer

        if self.dose_gy is None:
            raise RuntimeError("No hay datos de dosis para crear nodo 3D")

        # Usar labelmap o CT como referencia espacial
        ref_node = self.labelmap_node or self.ct_node
        if ref_node is None:
            raise RuntimeError("No hay nodo de referencia para crear volumen de dosis")

        from SlicerDosim.SlicerDosimLib.dosimetry import DoseCalculator

        calc = DoseCalculator()
        dose_node = calc.create_dose_volume(self.dose_gy, ref_node)

        if dose_node is None:
            raise RuntimeError("create_dose_volume devolvio None")

        self.dose_node = dose_node
        logger.info(f"  Nodo de dosis creado: '{dose_node.GetName()}'")

        # Mostrar dosis como overlay en slices
        try:
            ct_for_bg = self.ct_node
            slice_nodes = slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode")
            for sn in slice_nodes:
                if ct_for_bg:
                    sn.SetBackgroundVolumeID(ct_for_bg.GetID())
                sn.SetForegroundVolumeID(dose_node.GetID())
                sn.SetForegroundOpacity(0.5)
            slicer.util.setSliceViewerLayers(foreground=dose_node, foregroundOpacity=0.5)
            logger.info("  Overlay de dosis activado en slices")
        except Exception as e:
            logger.warning(f"  Error activando overlay: {e}")

    # ── 10. DVH en Slicer + guardar escena ──

    def _create_dvh_and_save(self):
        """Crea graficos DVH en Slicer y guarda escena final."""
        import slicer

        if self.dose_gy is not None and self.labelmap_array is not None:
            try:
                _create_dvh_plots_slicer(
                    self.dose_gy, self.labelmap_array, self.spacing, show_gui=True,
                )
                logger.info("  DVH graficado en Slicer")
            except Exception as e:
                logger.warning(f"  Error creando DVH plots: {e}")
        else:
            logger.warning("  DVH no disponible (sin labelmap o dosis)")

        # Guardar escena final
        scene_out = os.path.join(self.output_dir, "3Dosim_dosis_scene.mrb")
        try:
            old_tmp = os.environ.get("TMP", "")
            old_temp = os.environ.get("TEMP", "")
            try:
                short_tmp = r"C:\tmp"
                os.makedirs(short_tmp, exist_ok=True)
                os.environ["TMP"] = short_tmp
                os.environ["TEMP"] = short_tmp
                success = slicer.util.saveScene(scene_out)
            finally:
                os.environ["TMP"] = old_tmp
                os.environ["TEMP"] = old_temp

            if success:
                logger.info(f"  Escena final guardada: {scene_out}")
        except Exception as e:
            logger.warning(f"  No se pudo guardar escena final: {e}")

        # Mostrar Plots module
        try:
            slicer.util.selectModule("Plots")
            slicer.app.processEvents()
        except Exception:
            pass

        # Resumen en consola
        self._log_consola("=" * 50)
        self._log_consola("PIPELINE MODULO 3 COMPLETADO")
        self._log_consola(f"  Actividad: {self.activity_gbq:.4f} GBq")
        for name, s in self.results_data.get("structures", {}).items():
            label = {"higado": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}.get(name, name)
            self._log_consola(f"  {label}: Dmedia={s.get('mean_dose_gy', 0):.2f} Gy, "
                             f"BED={s.get('bed_gy', 0):.2f} Gy")
        if self.pdf_path:
            self._log_consola(f"  PDF: {os.path.basename(self.pdf_path)}")
        self._log_consola("=" * 50)

    # ==================================================================
    # AUTO-DETECT
    # ==================================================================

    @staticmethod
    def _auto_detect_scene():
        """Auto-detecta la escena .mrb mas reciente."""
        candidates = [
            r"C:\MAT\3Dosim\ai-pipe\scenes\3Dosim_scene.mrb",
            r"C:\MAT\3Dosim\ai-pipe\scenes\3Dosim.mrb",
            r"C:\MAT\3Dosim\ai-pipe\scenes\3Dosim_mod1_scene.mrb",
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


# ======================================================================
# CLI entry point (para ejecucion directa)
# ======================================================================

def main():
    """Entry point CLI para PipelineMod3."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline Mod3 - Analisis Dosimetrico desde escena + MCTAL"
    )
    parser.add_argument("--scene", default=None, help="Ruta al archivo .mrb")
    parser.add_argument("--mctal", default=None, help="Ruta al archivo MCTAL")
    parser.add_argument("--labelmap", default=None, help="Ruta a labelmap NIfTI")
    parser.add_argument("--activity", type=float, default=None,
                        help="Actividad en GBq (default: computar del PET)")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--reset", action="store_true", help="Reiniciar checkpoints")
    parser.add_argument("--flip", action="store_true", default=True,
                        help="Aplicar flip Y a dosis MCTAL (default: True)")
    parser.add_argument("--no-flip", action="store_false", dest="flip",
                        help="No aplicar flip Y a dosis MCTAL")
    parser.add_argument("--patient-id", default=None,
                        help="ID del paciente para el reporte")
    parser.add_argument("--no-consola", action="store_true",
                        help="Deshabilita la consola interactiva")
    args, _ = parser.parse_known_args()

    # Agregar paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)

    pipeline = PipelineMod3(
        scene_path=args.scene,
        mctal_path=args.mctal,
        labelmap_path=args.labelmap,
        activity_gbq=args.activity,
        output_dir=args.output,
        reset=args.reset,
        flip=args.flip,
        no_consola=args.no_consola,
        patient_id=args.patient_id,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
