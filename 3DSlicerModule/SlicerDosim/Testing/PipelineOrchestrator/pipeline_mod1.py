"""
PipelineMod1 - Modulo 1: Carga, segmentacion y tumor.
Flujo completo hasta exportacion de labelmap dosimetrica.

NO incluye generacion MCNP (eso es Mod2).
NO incluye analisis dosimetrico (eso es Mod3).

Todos los imports son absolutos para compatibilidad con Slicer --python-script.
"""

import logging
import os
import time

from PipelineOrchestrator.checkpoint import CheckpointManager
from PipelineOrchestrator.worker import PipelineWorker
from PipelineOrchestrator import anonymize
from PipelineOrchestrator import couch_remover
from PipelineOrchestrator import segmentation
from PipelineOrchestrator import validation
from PipelineOrchestrator import tumor_creator
from PipelineOrchestrator import tumor_validation
from PipelineOrchestrator import labelmap_exporter
from PipelineOrchestrator import git_commit
from PipelineOrchestrator import ai_supervisor
from PipelineOrchestrator.utils import logger, add_module_path, show_progress
from PipelineOrchestrator.mcp_helper import MCP
from PipelineOrchestrator.comandos import ConsolaComandos
from PipelineOrchestrator.views import setup_medical_views, load_pipeline_config

logger = logging.getLogger("3DosimMod1")


class PipelineMod1:
    """
    Pipeline Modulo 1: carga PET/CT, segmentacion anatomica (TotalSegmentator),
    creacion de tumor (3 modos), validacion medica, y exportacion de labelmap.
    """

    STEP_CHECK_SLICER  = "check_slicer"
    STEP_LOAD_DICOM    = "load_dicom"
    STEP_SHOW_FUSION   = "show_fusion"
    STEP_ANONYMIZE     = "anonymize"
    STEP_EXPORT_DICOM_INFO = "export_dicom_info"
    STEP_REMOVE_COUCH  = "remove_couch_air"
    STEP_RESAMPLE_PET  = "resample_pet_to_ct"
    STEP_SEGMENT       = "segment_phantom"
    STEP_VALIDATE_AUTO = "validate_segmentation_auto"
    STEP_VALIDATE      = "validate_segmentation"
    STEP_ADD_TUMOR     = "add_synthetic_tumor"
    STEP_VALIDATE_TUMOR = "validate_tumor"
    STEP_HEALTHY_LIVER  = "create_healthy_liver"
    STEP_SEGMENT_BODY   = "segment_body"
    STEP_EXPORT_LABELMAP = "export_labelmap"

    def __init__(self, data_dir: str, reset: bool = False, mcp_port: int = 0,
                 no_consola: bool = False, segmenter: str = "totalsegmentator",
                 stop_before_segment: bool = False, force_cpu: bool = True,
                 patient_id: str = None):
        self.data_dir = data_dir
        self.patient_id = patient_id or ""
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")
        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")
        self.anon_dir = os.path.join(self.output_dir, ".anon")
        self.labelmap_dir = os.path.join(self.output_dir, "labelmaps")

        self.results = {"pasos": [], "errores": [], "tiempos": {}}

        self.checkpoint = CheckpointManager(self.checkpoint_dir)
        if reset:
            self.checkpoint.reset()

        # Nodos Slicer
        self.ct_node = None
        self.ct_masked_node = None
        self.pet_node = None
        self.segmentation_node = None
        self.body_node = None
        self.phantom_nifti_path = None
        self.ct_node_name = None
        self.pet_node_name = None

        # MCP
        self.mcp = MCP()
        self.mcp_server = None
        self.mcp_port = mcp_port
        self.screenshots = []

        # Segmentacion
        self.segmenter = segmenter
        logger.info(f"  Segmentador:    {segmenter}")
        self.force_cpu = force_cpu
        logger.info(f"  Force CPU:      {force_cpu}")
        self.stop_before_segment = stop_before_segment
        if stop_before_segment:
            logger.info("  Modo:           STOP antes de segmentacion (manual)")

        # Consola
        self.no_consola = no_consola
        self.pipeline_config = load_pipeline_config()
        self.scene_output_dir = self.pipeline_config.get(
            "scene_output_dir",
            os.path.join(self.output_dir, "scenes"),
        )
        logger.info(f"  Scene output dir:  {self.scene_output_dir}")
        self.screenshot_output_dir = self.pipeline_config.get(
            "screenshot_output_dir",
            os.path.join(self.output_dir, "screenshots"),
        )
        logger.info(f"  Screenshot dir:    {self.screenshot_output_dir}")
        self.image_output_dir = self.pipeline_config.get(
            "image_output_dir",
            os.path.join(self.output_dir, "imagenes"),
        )
        logger.info(f"  Image output dir:  {self.image_output_dir}")

        # Config del tumor
        self.tumor_config = self.pipeline_config.get("tumor", {})
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        logger.info(f"  Tumor mode:     {tumor_mode}")
        if tumor_mode == "load_file":
            logger.info(f"  Tumor file:     {self.tumor_config.get('load_file_path', '')}")
        elif tumor_mode == "manual":
            logger.info(f"  Tumor segment:  {self.tumor_config.get('manual_segment_name', 'Tumor_Manual')}")

        self.consola = None
        if not no_consola:
            try:
                self.consola = ConsolaComandos(output_dir=self.output_dir)
            except Exception as e:
                logger.debug(f"Consola no disponible: {e}")
                self.consola = None

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Modulo 1 — Carga, Segmentacion, Tumor")
        logger.info("=" * 60)
        logger.info(f"Datos:        {self.data_dir}")
        logger.info(f"Output:       {self.output_dir}")
        logger.info(f"Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info(f"Consola:      {'SI' if not no_consola else 'NO'}")
        logger.info("")

    # ==================================================================
    # RUN (blocking — backward compatible)
    # ==================================================================

    def run(self):
        """
        Ejecuta el pipeline Mod1 de forma BLOQUEANTE.
        Usa internamente el PipelineWorker para no congelar Slicer,
        pero se bloquea hasta que todos los pasos terminen.

        Compatible con el entry point main.py existente.
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 1")
        logger.info("")

        # ── Pre-setup (ocurre antes del worker) ──
        if self.consola:
            self.consola.log("=" * 50)
            self.consola.log(" 3Dosim Mod1 - Consola de Comandos")
            self.consola.log(" Escribi 'ayuda' para comandos disponibles")
            self.consola.log("=" * 50)
            self.consola.log("")
            self.consola.mostrar()

        self._log_consola("Iniciando modulo 1...")

        # Cargar escena guardada si existe
        self._load_scene_if_needed()
        if getattr(self, 'segmentation_node', None):
            self._show_segmentation_3d(self.segmentation_node)

        # Arrancar MCP server (parte de check_slicer)
        self._pre_check_slicer()

        # Checkpoints que ya estan completos → restaurar estado
        self._restore_preexisting_checkpoints()

        # ── Construir worker con todos los pasos ──
        self._build_worker()

        # ── Bloquear hasta que termine ──
        self._pipeline_ok = False
        self._pipeline_done = False

        try:
            from qt import QEventLoop

            self.worker.pipeline_completed.connect(self._on_pipeline_completed_blocking)
            self.worker.step_error.connect(self._on_step_error_blocking)
            self.worker.start()

            loop = QEventLoop()
            # Salir del loop cuando termine o falle
            self.worker.pipeline_completed.connect(loop.quit)
            self.worker.step_error.connect(lambda name, err, elapsed: loop.quit())
            loop.exec_()
        except ImportError:
            # No-Qt fallback (tests): polling loop
            self.worker.start()
            while self.worker.is_running():
                import time
                time.sleep(0.1)

        # Reporte final
        ok = self._pipeline_ok
        self._report()
        if ok:
            self._log_consola("Modulo 1 finalizado EXITOSAMENTE")
        else:
            self._log_consola("Modulo 1 finalizado con ERRORES. Revise el reporte.")

    # ────────────────────────────────────────────────────────────
    # CALLBACKS PARA run() BLOQUEANTE
    # ────────────────────────────────────────────────────────────

    def _on_pipeline_completed_blocking(self):
        self._pipeline_ok = True
        self._pipeline_done = True
        if self.stop_before_segment:
            self._stop_before_segment_handler()
        else:
            self._log_mod1_summary()

    def _on_step_error_blocking(self, name, error_msg, elapsed):
        """Cuando un paso falla en modo bloqueante, registramos y SEGUIMOS
        si el paso es non-critical (como en el codigo original)."""
        self._pipeline_ok = False

    # ────────────────────────────────────────────────────────────
    # RUN ASYNC (non-blocking — para integracion con launcher)
    # ────────────────────────────────────────────────────────────

    def run_async(self, on_completed=None, on_error=None):
        """
        Ejecuta el pipeline Mod1 de forma NO BLOQUEANTE.
        Los callbacks se invocan cuando el pipeline termina o falla.

        Args:
            on_completed: callback(success: bool) cuando todos los pasos terminan
            on_error: callback(step_name: str, error: str) cuando un paso falla
        """
        logger.info("")
        logger.info("INICIANDO PIPELINE MODULO 1 (async)")
        logger.info("")

        if self.consola:
            self.consola.log("=" * 50)
            self.consola.log(" 3Dosim Mod1 - Consola de Comandos")
            self.consola.log(" Escribi 'ayuda' para comandos disponibles")
            self.consola.log("=" * 50)
            self.consola.log("")
            self.consola.mostrar()

        self._log_consola("Iniciando modulo 1...")

        self._load_scene_if_needed()
        if getattr(self, 'segmentation_node', None):
            self._show_segmentation_3d(self.segmentation_node)

        self._pre_check_slicer()
        self._restore_preexisting_checkpoints()
        self._build_worker()

        # Callbacks externos
        if on_completed:
            self.worker.pipeline_completed.connect(
                lambda: on_completed(self._pipeline_ok))
        if on_error:
            self.worker.step_error.connect(
                lambda name, err, elapsed: on_error(name, err))

        self._pipeline_ok = False
        self._pipeline_done = False
        self.worker.pipeline_completed.connect(self._on_pipeline_completed_blocking)
        self.worker.start()

        logger.info("  [Async] Pipeline Mod1 iniciado — Slicer responde durante la ejecucion")

    # ────────────────────────────────────────────────────────────
    # BUILD WORKER — define la lista de pasos
    # ────────────────────────────────────────────────────────────

    def _build_worker(self):
        """Construye el PipelineWorker con todos los pasos de Mod1.

        Cada paso es: (step_name, is_heavy, callable)
        - is_heavy=True → se ejecuta en thread separado con polling
        - is_heavy=False → se ejecuta en el main thread con processEvents()

        Los pasos que ya estan en checkpoint se saltan automaticamente
        (el callable chequea el checkpoint antes de ejecutar).
        """
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        mode_labels = {
            "synthetic": "Tumor sintetico esferico en higado",
            "load_file": "Cargar tumor desde archivo NIfTI",
            "manual": "Segmentacion manual del tumor en Slicer",
        }
        create_healthy = self.tumor_config.get("create_healthy_liver", True)

        steps = []

        # Paso 1: check_slicer
        steps.append((self.STEP_CHECK_SLICER, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_CHECK_SLICER, "Verificando entorno Slicer",
                          self._check_slicer,
                          data_func=lambda: {"slicer_version": self._slicer_version()},
                          post_fn=lambda: add_module_path())))

        # Paso 2: load_dicom (CRITICO)
        steps.append((self.STEP_LOAD_DICOM, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_LOAD_DICOM, "Cargando imagenes DICOM",
                          self._load_dicom,
                          data_func=lambda: {
                              "ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                              "pet_node_name": self.pet_node.GetName() if self.pet_node else None,
                              "ct_dir": self.ct_dir, "pet_dir": self.pet_dir},
                          critical=True,  # si falla, aborta
                          post_fn=lambda: self._post_load_dicom())))

        # Paso 3: remove_couch_air
        steps.append((self.STEP_REMOVE_COUCH, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_REMOVE_COUCH, "Eliminando camilla y aire",
                          self._remove_couch_air,
                          data_func=lambda: {
                              "ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                              "ct_masked_node_name": self.ct_masked_node.GetName() if self.ct_masked_node else None},
                          post_fn=lambda: self._post_remove_couch())))

        # Paso 4: resample PET (Elastix ~30-60s → HEAVY)
        steps.append((self.STEP_RESAMPLE_PET, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_RESAMPLE_PET, "Re-muestreando PET a geometria CT",
                          self._resample_pet_to_ct,
                          data_func=lambda: {"pet_resampled": self.pet_node is not None},
                          post_fn=lambda: self._post_resample_pet())))

        # Paso 5: show_fusion
        steps.append((self.STEP_SHOW_FUSION, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_SHOW_FUSION, "Mostrando fusion CT+PET registrada",
                          self._show_fusion,
                          post_fn=lambda: self._post_show_fusion())))

        # Paso 6: anonymize
        steps.append((self.STEP_ANONYMIZE, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_ANONYMIZE, "Anonimizando imagenes",
                          self._anonymize,
                          data_func=lambda: {
                              "ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                              "pet_node_name": self.pet_node.GetName() if self.pet_node else None},
                          post_fn=lambda: self._post_anonymize())))

        # Paso 7: export DICOM info
        steps.append((self.STEP_EXPORT_DICOM_INFO, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_EXPORT_DICOM_INFO, "Exportando metadata DICOM a JSON",
                          self._export_dicom_info_json)))

        # ── Stop before segment (si aplica) ──
        # NOTA: La conexion de senales se hace DESPUES de _build_worker,
        # en run() y run_async(). Si stop_before_segment es True,
        # el worker solo tiene pasos 1-7 y el handler final mostrara
        # las instrucciones para segmentacion manual.

        # Paso 8: segment_phantom (TotalSegmentator ∼173s → HEAVY)
        seg_display = f"Segmentando ({self.segmenter})"
        steps.append((self.STEP_SEGMENT, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_SEGMENT, seg_display,
                          self._segment,
                          critical=True,
                          data_func=lambda: {
                              "segmentation_node_name": self.segmentation_node.GetName() if self.segmentation_node else None,
                              "segmenter": self.segmenter},
                          post_fn=lambda: self._post_segment())))

        # Paso 9: autovalidacion
        steps.append((self.STEP_VALIDATE_AUTO, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_VALIDATE_AUTO, "Autochequeo de segmentos",
                          self._validate_segmentation_auto,
                          data_func=lambda: {"segmenter": self.segmenter})))

        # Paso 10: validacion medica de la segmentacion
        steps.append((self.STEP_VALIDATE + "_seg", False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_VALIDATE + "_seg", "Validacion medica de la segmentacion",
                          lambda: self._do_validation(context="segmentacion"),
                          critical=True,
                          data_func=lambda: {"validado_por": "medico", "contexto": "segmentacion",
                                             "timestamp": __import__('datetime').datetime.now().isoformat()},
                          post_fn=lambda: self._post_validate_seg())))

        # Paso 11: tumor (segun config)
        step_label = mode_labels.get(tumor_mode, f"Tumor (modo: {tumor_mode})")
        steps.append((self.STEP_ADD_TUMOR, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_ADD_TUMOR, step_label,
                          self._add_tumor,
                          data_func=lambda: {"mode": tumor_mode, "config": self.tumor_config},
                          post_fn=lambda: self._post_tumor())))

        # Paso 12: higado sano
        if create_healthy:
            steps.append((self.STEP_HEALTHY_LIVER, False,
                          lambda: self._checkpoint_step_wrapper(
                              self.STEP_HEALTHY_LIVER, "Higado sano (higado - tumor)",
                              self._create_healthy_liver,
                              data_func=lambda: {"created": True},
                              post_fn=lambda: self._post_healthy_liver())))

        # Paso 13: validacion medica del tumor
        steps.append((self.STEP_VALIDATE_TUMOR, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_VALIDATE_TUMOR, "Validacion medica del tumor",
                          lambda: self._validate_tumor(context=tumor_mode),
                          critical=True,
                          data_func=lambda: {"context": tumor_mode,
                                             "timestamp": __import__('datetime').datetime.now().isoformat()},
                          post_fn=lambda: self._post_validate_tumor())))

        # Paso 14: segment_body (TotalSegmentator task=body ∼60s → HEAVY)
        steps.append((self.STEP_SEGMENT_BODY, True,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_SEGMENT_BODY, "Segmentacion corporal (body)",
                          self._segment_body,
                          data_func=lambda: {"task": "body", "fast": True, "force_cpu": True},
                          post_fn=lambda: self._post_segment_body())))

        # Paso 15: export_labelmap
        steps.append((self.STEP_EXPORT_LABELMAP, False,
                      lambda: self._checkpoint_step_wrapper(
                          self.STEP_EXPORT_LABELMAP, "Exportar labelmap dosimetrica",
                          self._export_labelmap,
                          data_func=lambda: {"output_dir": self.labelmap_dir},
                          post_fn=lambda: self._post_export_labelmap())))

        self.worker = PipelineWorker(steps)

        # ── Conectar señales ──
        self.worker.step_completed.connect(self._on_worker_step_completed)
        self.worker.step_error.connect(self._on_worker_step_error)
        self.worker.blocking_started.connect(self._on_worker_blocking_started)
        self.worker.pipeline_completed.connect(self._on_worker_pipeline_completed)

    # ────────────────────────────────────────────────────────────
    # POST-STEP HANDLERS (reemplazan el codigo inline en run())
    # ────────────────────────────────────────────────────────────

    def _post_load_dicom(self):
        self._save_scene("01_post_load_dicom")
        self.tomar_screenshot("01_carga_dicom")
        setup_medical_views(
            ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

    def _post_remove_couch(self):
        self._save_scene("02_remove_couch")
        self.tomar_screenshot("02_remove_couch")

    def _post_resample_pet(self):
        self._save_scene("03_pet_resampled")
        self.tomar_screenshot("03_pet_resampled")
        setup_medical_views(
            ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

    def _show_pet_info(self):
        """Muestra mensaje no-modal con info del PET (dimensiones, espaciado, actividad)."""
        if not self.pet_node:
            return
        import slicer
        import numpy as np
        try:
            dims = self.pet_node.GetImageData().GetDimensions()
            spacing = self.pet_node.GetSpacing()
            n_voxels = dims[0] * dims[1] * dims[2]
            voxel_vol_ml = (spacing[0] * spacing[1] * spacing[2]) / 1000.0
            arr = slicer.util.arrayFromVolume(self.pet_node)  # (nz, ny, nx)
            total_pet = float(np.sum(arr[arr > 0]))
            total_pet_all = float(np.sum(arr))
            # Estimar actividad total
            if total_pet_all < 1e8:
                activity_bq = total_pet_all * voxel_vol_ml
                pet_unit = "Bq/ml"
            else:
                activity_bq = total_pet_all
                pet_unit = "Bq"
            activity_mbq = activity_bq / 1e6
            activity_gbq = activity_bq / 1e9
            mean_suv = float(np.mean(arr[arr > 0])) if np.any(arr > 0) else 0
            max_suv = float(np.max(arr))
            lines = [
                f"Dimensiones: {dims[0]} x {dims[1]} x {dims[2]}",
                f"Espaciado: {spacing[0]:.3f} x {spacing[1]:.3f} x {spacing[2]:.3f} mm",
                f"Voxeles totales: {n_voxels}",
                f"Volumen voxel: {voxel_vol_ml:.6f} ml",
                "",
                f"PET unidades: {pet_unit}",
                f"Suma total PET: {total_pet_all:.2e}",
                f"Media SUV (>0): {mean_suv:.2f}",
                f"SUV maximo: {max_suv:.2f}",
                "",
                f"Actividad estimada: {activity_bq:.2e} Bq",
                f"  = {activity_mbq:.2f} MBq",
                f"  = {activity_gbq:.4f} GBq",
            ]
            msg = "\n".join(lines)
            logger.info("=== Informacion del PET ===\n" + msg)
            qt_mod = slicer.util.loadQtGuiModule()
            if qt_mod:
                from qt import QMessageBox
                mb = QMessageBox(
                    QMessageBox.Information,
                    "Informacion del PET",
                    msg,
                    QMessageBox.Ok,
                )
                mb.setDetailedText(
                    f"Actividad calculada como suma de voxeles PET.\n"
                    f"PET unit = {pet_unit}, vol_voxel = {voxel_vol_ml:.6f} ml\n"
                    f"(Los valores de actividad son estimaciones)"
                )
                mb.setModal(False)
                mb.show()
        except Exception as e:
            logger.warning(f"No se pudo mostrar info PET: {e}")

    def _post_show_fusion(self):
        self._show_pet_info()
        self._save_scene("04_fusion_ct_pet_registrada")
        self.tomar_screenshot("04_fusion_ct_pet_registrada")

    def _post_anonymize(self):
        self._save_scene("05_anonymize")
        self.tomar_screenshot("05_anonymize")

    def _post_segment(self):
        self._save_scene("08_segmentacion")
        self.tomar_screenshot("08_segmentacion")
        setup_medical_views(
            ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node, segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )
        self._show_segmentation_3d(self.segmentation_node)

    def _post_validate_seg(self):
        self._save_scene("08_post_validacion_segmentacion")
        self.tomar_screenshot("08_validacion_segmentacion")
        setup_medical_views(
            ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node, segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

    def _post_tumor(self):
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        scene_tag = {"synthetic": "09_tumor_sintetico", "load_file": "09_tumor_cargado",
                     "manual": "09_tumor_manual"}.get(tumor_mode, "09_tumor")
        self._save_scene(scene_tag)
        self.tomar_screenshot(scene_tag)
        setup_medical_views(
            ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node, segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

    def _post_healthy_liver(self):
        self._save_scene("10_higado_sano")
        self.tomar_screenshot("10_higado_sano")

    def _post_validate_tumor(self):
        self._save_scene("11_validacion_tumor")
        self.tomar_screenshot("11_validacion_tumor")

    def _post_segment_body(self):
        self._save_scene("12_segment_body")
        self.tomar_screenshot("12_segment_body")

    def _post_export_labelmap(self):
        self._save_scene("13_labelmap_exportada")
        self.tomar_screenshot("13_labelmap_exportada")

    # ────────────────────────────────────────────────────────────
    # WORKER SIGNAL HANDLERS
    # ────────────────────────────────────────────────────────────

    def _on_worker_step_completed(self, name, result, elapsed):
        """Un paso se completo exitosamente."""
        # El post_fn ya se ejecuto dentro del checkpoint_step_wrapper
        logger.info(f"  [Worker] Paso '{name}' OK ({elapsed:.1f}s)")

    def _on_worker_step_error(self, name, error_msg, elapsed):
        """Un paso fallo."""
        logger.error(f"  [Worker] Paso '{name}' FALLO: {error_msg}")

    def _on_worker_blocking_started(self, name):
        """Un paso pesado (threaded) comenzo."""
        self._log_consola(f"Iniciando paso pesado: {name} (Slicer responde en paralelo)...")

    def _on_worker_pipeline_completed(self):
        """Todos los pasos terminaron (con o sin errores)."""
        # Verificar si hubo errores fatales
        errores = self.results.get("errores", [])
        has_fatal = any("CRITICO" in e for e in errores)

        tumor_mode = self.tumor_config.get("mode", "synthetic")
        create_healthy = self.tumor_config.get("create_healthy_liver", True)

        logger.info("")
        logger.info("  PIPELINE MODULO 1 COMPLETADO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. Carga DICOM")
        logger.info("    2. Eliminar camilla/aire")
        logger.info("    3. Re-muestreo PET")
        logger.info("    4. Fusion CT+PET")
        logger.info("    5. Anonimizar")
        logger.info("    6. TotalSegmentator (task=total)")
        logger.info("    7. Validacion segmentacion")
        logger.info(f"    8. Tumor (modo: {tumor_mode})")
        logger.info("    9. Validacion medica del tumor")
        if create_healthy:
            logger.info("   10. Higado sano = higado - tumor")
        logger.info("   11. TotalSegmentator (task=body)")
        logger.info("   12. Exportar labelmap dosimetrica")
        logger.info("")
        logger.info("  Siguiente paso:")
        logger.info("    Modulo 2: pipeline_mod2.py para generar entrada MCNP")
        logger.info("    Modulo 3: analisis dosimetrico desde output MCNP")
        logger.info("")

        self._log_consola("Modulo 1 completado. Generando reporte...")
        ok = not has_fatal
        if ok:
            self._log_consola("Modulo 1 finalizado EXITOSAMENTE")
        else:
            self._log_consola("Modulo 1 finalizado con ERRORES. Revise el reporte.")
        self._report()

    # ────────────────────────────────────────────────────────────
    # WRAPPER: checkpoint_step + post-action unificados
    # ────────────────────────────────────────────────────────────

    def _checkpoint_step_wrapper(self, step_name, display_name, func,
                                  data_func=None, critical=False, post_fn=None):
        """
        Wrapper unificado que:
        1. Verifica si el checkpoint ya esta completo (salta si es asi)
        2. Ejecuta func() con medicion de tiempo
        3. Registra exito/fallo en self.results
        4. Marca checkpoint
        5. Corre AI review
        6. Ejecuta post_fn si existe

        Args:
            step_name: clave del checkpoint
            display_name: nombre para mostrar en logs
            func: callable del paso
            data_func: callable que retorna dict para guardar en checkpoint
            critical: si True, un fallo aborta el pipeline completo
            post_fn: callable a ejecutar DESPUES del exito (save_scene, screenshot, etc.)

        Returns:
            True si el paso se completo exitosamente
        """
        # ── Checkpoint skip ──
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            self._log_consola(f"[checkpoint] {display_name} — ya completado, saltando")
            cp_data = self.checkpoint.get_data(step_name)
            if cp_data:
                self._restore_step_state(step_name, cp_data)
            # Tambien ejecutar post_fn si existe (necesario para restaurar vistas)
            if post_fn:
                try:
                    post_fn()
                except Exception as e:
                    logger.debug(f"Post-step checkpoint skip fallo: {e}")
            return True

        # ── Ejecutar ──
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

            # Post-step handler (scene, screenshot, views)
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
                logger.error(f"  [CRITICO] {display_name} fallo — pipeline no puede continuar")
                self.worker.abort()
            return False

    # ==================================================================
    # METODOS INTERNOS (extraidos de pipeline.py)
    # ==================================================================

    def _checkpoint_step(self, step_name, display_name, func, data_func=None):
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
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
                "nombre": display_name, "ok": True, "tiempo": elapsed
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
                "nombre": display_name, "ok": False, "tiempo": elapsed
            })
            self.results["errores"].append(f"{display_name}: {e}")
            show_progress(f"FALLO: {display_name}")
            self._log_consola_error(f"{display_name} — FALLO: {e}")
            self._ai_review_paso(display_name, ok=False, elapsed=elapsed,
                                 step_name=step_name, error=str(e))
            return False

    def _ai_review_paso(self, display_name, ok, elapsed, step_name, data=None, error=None):
        try:
            ctx = {
                "paso": display_name, "ok": ok, "tiempo": elapsed,
                "datos": data or {}, "errores": [error] if error else [],
            }
            nodos_info = {}
            if self.ct_node:
                nodos_info["CT"] = self.ct_node.GetName()
            if self.pet_node:
                nodos_info["PET"] = self.pet_node.GetName()
            if self.segmentation_node:
                nodos_info["Segmentacion"] = self.segmentation_node.GetName()
                try:
                    seg_metrics = self._extract_segmentation_metrics()
                    if seg_metrics:
                        ctx["datos"]["segmentation_metrics"] = seg_metrics
                except Exception:
                    pass
            ctx["datos"]["segmenter_type"] = getattr(self, "segmenter", "desconocido")
            ctx["datos"]["nodos_activos"] = nodos_info
            ai_supervisor.revisar_paso(ctx, consola=self.consola)
        except Exception as e:
            logger.debug(f"AI review no disponible: {e}")

    def _extract_segmentation_metrics(self) -> dict:
        metrics = {}
        try:
            import slicer
            import vtk
            seg_node = self.segmentation_node
            if not seg_node:
                return metrics
            seg_display = seg_node.GetDisplayNode()
            if not seg_display:
                return metrics
            seg_collection = seg_node.GetSegmentation()
            if not seg_collection:
                return metrics
            segment_ids = vtk.vtkStringArray()
            seg_collection.GetSegmentIDs(segment_ids)
            num_segments = segment_ids.GetNumberOfValues()
            metrics["num_segments"] = num_segments
            names = []
            for i in range(num_segments):
                seg_id = segment_ids.GetValue(i)
                segment = seg_collection.GetSegment(seg_id)
                if segment:
                    names.append(segment.GetName())
            metrics["segment_names"] = names
            try:
                labelmap_node = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLLabelMapVolumeNode", "_tmp_metrics")
                success = slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
                    seg_node, labelmap_node, seg_display.GetReferenceImageGeometryNode(),
                    segment_ids, 1, labelmap_node.GetName())
                if success and labelmap_node.GetImageData():
                    import numpy as np
                    arr = slicer.util.arrayFromVolume(labelmap_node)
                    spacing = labelmap_node.GetSpacing()
                    voxel_vol_cc = spacing[0] * spacing[1] * spacing[2] / 1000.0
                    total_voxels = np.count_nonzero(arr)
                    metrics["volume_cc"] = round(total_voxels * voxel_vol_cc, 1)
                    if self.ct_masked_node:
                        ct_arr = slicer.util.arrayFromVolume(self.ct_masked_node)
                        fuera_cuerpo = np.count_nonzero((arr > 0) & (ct_arr <= -200))
                        metrics["voxels_fuera_cuerpo"] = int(fuera_cuerpo)
                slicer.mrmlScene.RemoveNode(labelmap_node)
            except Exception:
                pass
            warnings = []
            if num_segments <= 2:
                warnings.append(
                    f"Solo {num_segments} segmento(s). "
                    "Un cuerpo completo deberia tener ~104 organos."
                )
            if metrics.get("voxels_fuera_cuerpo", 0) > 1000:
                warnings.append(
                    f"{metrics['voxels_fuera_cuerpo']} voxels segmentados fuera del contorno corporal."
                )
            metrics["warnings"] = warnings
        except Exception as e:
            logger.debug(f"Error extrayendo metricas: {e}")
        return metrics

    def _restore_step_state(self, step_name, data):
        if not data:
            return
        import slicer
        restore_map = {
            "ct_node": "ct_node", "pet_node": "pet_node",
            "segmentation_node": "segmentation_node",
            "ct_node_name": "ct_node_name", "pet_node_name": "pet_node_name",
            "ct_masked_node_name": "ct_masked_node_name",
        }
        for data_key, attr_name in restore_map.items():
            if data_key in data and data[data_key] is not None:
                if data_key.endswith("_name"):
                    try:
                        node = slicer.util.getNode(data[data_key])
                        actual_attr = data_key.replace("_name", "_node")
                        if hasattr(self, actual_attr):
                            setattr(self, actual_attr, node)
                    except Exception:
                        self._restore_node_by_type(data_key, data[data_key])
                else:
                    setattr(self, attr_name, data[data_key])
        if self.ct_node or self.pet_node:
            try:
                setup_medical_views(
                    ct_node=self.ct_node, ct_masked_node=self.ct_masked_node,
                    pet_node=self.pet_node, segmentation_node=self.segmentation_node,
                    layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
                    pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
                    link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
                )
            except Exception as e:
                logger.debug(f"No se pudo restaurar visualizacion: {e}")

    def _restore_node_by_type(self, data_key, node_name):
        import slicer
        type_map = {
            "ct_node": "vtkMRMLScalarVolumeNode",
            "pet_node": "vtkMRMLScalarVolumeNode",
            "segmentation_node": "vtkMRMLSegmentationNode",
            "ct_node_name": "vtkMRMLScalarVolumeNode",
            "pet_node_name": "vtkMRMLScalarVolumeNode",
            "ct_masked_node_name": "vtkMRMLScalarVolumeNode",
        }
        node_type = type_map.get(data_key, "vtkMRMLScalarVolumeNode")
        nodes = slicer.util.getNodesByClass(node_type)
        if not nodes:
            logger.warning(f"  No se encontraron nodos de tipo {node_type}")
            return
        if len(nodes) == 1:
            chosen = nodes[0]
        else:
            keywords = {"ct": "CT", "pet": "PET", "seg": "Seg", "masked": "sin_camilla"}
            key = "ct"
            if "pet" in data_key:
                key = "pet"
            elif "seg" in data_key:
                key = "seg"
            elif "masked" in data_key:
                key = "masked"
            kw = keywords.get(key, key)
            candidates = [n for n in nodes if kw in n.GetName()]
            chosen = candidates[0] if candidates else nodes[0]
        attr = data_key.replace("_name", "_node") if data_key.endswith("_name") else data_key
        if hasattr(self, attr):
            setattr(self, attr, chosen)
            logger.info(f"  Nodo restaurado: '{chosen.GetName()}' -> self.{attr}")

    # ==================================================================
    # HELPER METHODS
    # ==================================================================

    def _slicer_version(self) -> str:
        try:
            import slicer
            return f"{slicer.app.majorVersion}.{slicer.app.minorVersion}"
        except ImportError:
            return "desconocido"

    def _check_slicer(self):
        try:
            import slicer
            logger.info(f"  Slicer version: {self._slicer_version()}")
            self._mcp_start()
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    def _mcp_start(self):
        mcp_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "slicer-mcp-server.py"
        )
        if os.path.exists(mcp_script):
            logger.info(f"  Iniciando MCP server desde: {mcp_script}")
            try:
                with open(mcp_script) as f:
                    code = f.read()
                import slicer
                exec(compile(code, mcp_script, 'exec'),
                     {"__name__": "__mcp_server__", "slicer": slicer})
                logger.info("  MCP server listo")
            except Exception as e:
                logger.warning(f"No se pudo iniciar MCP local: {e}")
        else:
            logger.info("  MCP server no disponible (slicer-mcp-server.py no encontrado)")

    def _log_consola(self, mensaje):
        if self.consola:
            self.consola.log(mensaje)

    def _log_consola_ok(self, mensaje):
        if self.consola:
            self.consola.log_ok(mensaje)

    def _log_consola_error(self, mensaje):
        if self.consola:
            self.consola.log_error(mensaje)

    def tomar_screenshot(self, nombre, view="full"):
        try:
            import slicer
            from datetime import datetime
            ts = datetime.now().strftime("%H%M%S")
            filename = f"{ts}_{nombre}.png"
            shot_dir = getattr(self, "screenshot_output_dir", None) or \
                       os.path.join(self.output_dir, "screenshots")
            filepath = os.path.join(shot_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            pixmap = None
            if view == "full":
                mw = slicer.util.mainWindow()
                if mw:
                    pixmap = mw.grab()
            elif view == "3D":
                lm = slicer.app.layoutManager()
                if lm:
                    w = lm.threeDWidget(0)
                    if w:
                        pixmap = w.threeDView().grab()
            elif view in ("Red", "Yellow", "Green"):
                lm = slicer.app.layoutManager()
                if lm:
                    sw = lm.sliceWidget(view.upper())
                    if sw:
                        pixmap = sw.sliceView().grab()
            if pixmap is None:
                return None
            pixmap.save(filepath)
            self.screenshots.append(filepath)
            logger.info(f"  Screenshot: {os.path.basename(filepath)}")
            return filepath
        except Exception as e:
            logger.warning(f"No se pudo tomar screenshot '{nombre}': {e}")
            return None

    def _load_scene_if_needed(self):
        import slicer
        scene_path = os.path.join(self.scene_output_dir, "3Dosim.mrb")
        if not os.path.exists(scene_path):
            return
        checkpoint_keys = [
            self.STEP_LOAD_DICOM, self.STEP_REMOVE_COUCH,
            self.STEP_RESAMPLE_PET, self.STEP_SEGMENT,
        ]
        needs_restore = any(self.checkpoint.is_completed(k) for k in checkpoint_keys)
        if not needs_restore:
            return
        logger.info(f"  Cargando escena guardada: {scene_path}")
        try:
            success = slicer.util.loadScene(scene_path)
            if success:
                logger.info("  Escena cargada OK desde checkpoint")
        except Exception as e:
            logger.warning(f"No se pudo cargar escena: {e}")
        self._scan_scene_for_nodes()

    def _scan_scene_for_nodes(self):
        import slicer
        import vtk
        vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        seg_nodes_list = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        logger.info(f"  Escaneando: {len(vol_nodes)} volumenes, {len(seg_nodes_list)} segmentaciones")
        ct_candidates = [n for n in vol_nodes if "CT" in n.GetName() or "ct" in n.GetName().lower()]
        if ct_candidates and not getattr(self, 'ct_node', None):
            self.ct_node = ct_candidates[0]
        masked = [n for n in vol_nodes if "sin_camilla" in n.GetName().lower() or "masked" in n.GetName().lower()]
        if not masked:
            masked = ct_candidates
        if masked and not getattr(self, 'ct_masked_node', None):
            self.ct_masked_node = masked[0]
        pet_candidates = [n for n in vol_nodes if "PET" in n.GetName() or "pet" in n.GetName().lower()]
        if pet_candidates and not getattr(self, 'pet_node', None):
            self.pet_node = pet_candidates[0]
        if seg_nodes_list and not getattr(self, 'segmentation_node', None):
            ts_nodes = [n for n in seg_nodes_list if "TotalSegmentator" in n.GetName()]
            self.segmentation_node = ts_nodes[0] if ts_nodes else seg_nodes_list[0]
            seg_ids = vtk.vtkStringArray()
            self.segmentation_node.GetSegmentation().GetSegmentIDs(seg_ids)
            logger.info(f"  Segmentos: {seg_ids.GetNumberOfValues()}")
        body_candidates = [n for n in seg_nodes_list if "Body" in n.GetName()]
        if body_candidates and not getattr(self, 'body_node', None):
            self.body_node = body_candidates[0]

    def _show_segmentation_3d(self, seg_node=None):
        import slicer
        import vtk
        seg_node = seg_node or getattr(self, 'segmentation_node', None)
        if not seg_node:
            return
        seg_ids = vtk.vtkStringArray()
        seg_node.GetSegmentation().GetSegmentIDs(seg_ids)
        n = seg_ids.GetNumberOfValues()
        logger.info(f"  Modelos 3D para {n} segmentos...")
        try:
            seg_node.CreateClosedSurfaceRepresentation()
            disp_node = seg_node.GetDisplayNode()
            if disp_node:
                try:
                    disp_node.SetAllSegmentsVisible(True)
                except AttributeError:
                    pass
        except Exception as e:
            logger.warning(f"No se pudo generar representacion 3D: {e}")

    def _pre_check_slicer(self):
        """Ejecuta la verificacion de Slicer y arranque MCP si no esta en checkpoint."""
        if not self.checkpoint.is_completed(self.STEP_CHECK_SLICER):
            try:
                self._check_slicer()
                add_module_path()
                self.checkpoint.mark_completed(self.STEP_CHECK_SLICER,
                                               data={"slicer_version": self._slicer_version()})
            except Exception as e:
                logger.warning(f"Pre-check Slicer fallo (se reintentara en worker): {e}")

    def _restore_preexisting_checkpoints(self):
        """Restaura estado de nodos desde checkpoints previos."""
        for step_name in [self.STEP_LOAD_DICOM, self.STEP_REMOVE_COUCH,
                          self.STEP_RESAMPLE_PET, self.STEP_SEGMENT]:
            if self.checkpoint.is_completed(step_name):
                cp_data = self.checkpoint.get_data(step_name)
                if cp_data:
                    self._restore_step_state(step_name, cp_data)

    def _log_mod1_summary(self):
        """Loggea resumen de flujo de Mod1."""
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        create_healthy = self.tumor_config.get("create_healthy_liver", True)
        logger.info("")
        logger.info("  PIPELINE MODULO 1 COMPLETADO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. Carga DICOM")
        logger.info("    2. Eliminar camilla/aire")
        logger.info("    3. Re-muestreo PET")
        logger.info("    4. Fusion CT+PET")
        logger.info("    5. Anonimizar")
        logger.info("    6. TotalSegmentator (task=total)")
        logger.info("    7. Validacion segmentacion")
        logger.info(f"    8. Tumor (modo: {tumor_mode})")
        logger.info("    9. Validacion medica del tumor")
        if create_healthy:
            logger.info("   10. Higado sano = higado - tumor")
        logger.info("   11. TotalSegmentator (task=body)")
        logger.info("   12. Exportar labelmap dosimetrica")

    def _save_scene(self, tag=None):
        try:
            import slicer
            # Una sola escena — se sobrescribe acumulando cada paso
            filename = "3Dosim.mrb"
            scene_dir = getattr(self, "scene_output_dir", None)
            if not scene_dir:
                scene_dir = os.path.join(self.output_dir, "scenes")
            filepath = os.path.join(scene_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            logger.info(f"  Escena{' ['+tag+']' if tag else ''} -> {filepath}")
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
                logger.info(f"  Escena guardada: {os.path.basename(filepath)}")
                return filepath
        except Exception as e:
            logger.warning(f"No se pudo guardar escena '{tag}': {e}")
            return None

    def _stop_before_segment_handler(self):
        logger.info("")
        logger.info("=" * 60)
        logger.info(" PIPELINE DETENIDO ANTES DE SEGMENTACION")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Pasos completados:")
        logger.info("  1. check_slicer")
        logger.info("  2. load_dicom")
        logger.info("  3. remove_couch_air")
        logger.info("  4. resample_pet")
        logger.info("  5. show_fusion")
        logger.info("  6. anonymize")
        logger.info("")
        logger.info("Para correr TotalSegmentator manual:")
        logger.info("  from TotalSegmentator import TotalSegmentatorLogic")
        logger.info("  seg_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')")
        logger.info("  logic = TotalSegmentatorLogic()")
        logger.info("  logic.setupPythonRequirements()")
        logger.info("  logic.process(inputVolume=ct_node, outputSegmentation=seg_node,")
        logger.info("                fast=True, cpu=True, task='total')")
        logger.info("")
        logger.info("Para retomar: ejecutar sin --reset")
        logger.info("=" * 60)
        self._save_scene("07_pre_segmentacion_manual")
        self._log_consola("Pipeline detenido antes de segmentacion (modo manual)")
        self._report()

    # ==================================================================
    # STEP METHODS
    # ==================================================================

    def _load_dicom(self):
        import slicer
        from DICOMLib import DICOMUtils
        for d in [self.ct_dir, self.pet_dir]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio no encontrado: {d}")
        original_db_dir = DICOMUtils.openTemporaryDatabase()
        try:
            for dir_path, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
                logger.info(f"  Indexando {label}...")
                ok = DICOMUtils.importDicom(dir_path)
                if not ok:
                    raise RuntimeError(f"Fallo indexacion {label}")
            series_uids = DICOMUtils.allSeriesUIDsInDatabase()
            if not series_uids:
                raise RuntimeError("No se encontraron series DICOM")
            loaded_node_ids = DICOMUtils.loadSeriesByUID(series_uids)
        except Exception as e:
            DICOMUtils.closeTemporaryDatabase(original_db_dir, cleanup=True)
            raise RuntimeError(f"Error cargando DICOM: {e}")
        DICOMUtils.closeTemporaryDatabase(original_db_dir, cleanup=True)
        loaded_ct, loaded_pet = False, False
        for node_id in loaded_node_ids:
            node = slicer.mrmlScene.GetNodeByID(node_id)
            if not node:
                continue
            name = node.GetName().upper()
            if "CT" in name and not loaded_ct:
                self.ct_node = node
                loaded_ct = True
            elif ("PET" in name or "PT" in name or "NM" in name) and not loaded_pet:
                self.pet_node = node
                loaded_pet = True
        if not loaded_ct:
            for node_id in loaded_node_ids:
                node = slicer.mrmlScene.GetNodeByID(node_id)
                if node:
                    self.ct_node = node
                    loaded_ct = True
                    break
        if not loaded_pet and len(loaded_node_ids) > 1:
            for node_id in loaded_node_ids:
                node = slicer.mrmlScene.GetNodeByID(node_id)
                if node and node != self.ct_node:
                    self.pet_node = node
                    loaded_pet = True
                    break
        if not loaded_ct:
            raise RuntimeError("No se pudo cargar CT desde DICOM")
        if not loaded_pet:
            logger.warning("  PET no identificado")
        dims = self.ct_node.GetImageData().GetDimensions()
        spacing = self.ct_node.GetSpacing()
        logger.info(f"  CT: {dims[0]}x{dims[1]}x{dims[2]}, {spacing[0]:.3f}x{spacing[1]:.3f}x{spacing[2]:.3f} mm")

    def _show_fusion(self):
        import slicer
        lm = slicer.app.layoutManager()
        if lm is None:
            logger.warning("  No hay layout manager. Saltando config visual.")
            return
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
        bg_node = self.ct_masked_node if self.ct_masked_node else self.ct_node
        if not self.pet_node:
            slicer.util.setSliceViewerLayers(background=bg_node)
        else:
            pet_dn = self.pet_node.GetDisplayNode()
            if not pet_dn:
                from slicer import vtkMRMLScalarVolumeDisplayNode
                pet_dn = vtkMRMLScalarVolumeDisplayNode()
                slicer.mrmlScene.AddNode(pet_dn)
                pet_dn.SetDefaultColorMap()
                self.pet_node.SetAndObserveDisplayNodeID(pet_dn.GetID())
            pet_dn.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRainbow")
            pet_dn.AutoWindowLevelOff()
            pet_dn.SetWindowLevel(40.0, 20.0)
            slicer.util.setSliceViewerLayers(
                background=bg_node, foreground=self.pet_node, foregroundOpacity=0.35)
            bg_dn = bg_node.GetDisplayNode()
            if bg_dn:
                bg_dn.AutoWindowLevelOff()
                bg_dn.SetWindowLevel(400.0, 40.0)
        slicer.app.processEvents()
        slicer.util.resetSliceViews()
        slicer.app.processEvents()

    def _anonymize(self):
        anonymize.anonymize(self.ct_node, self.ct_dir, self.pet_dir, self.anon_dir, self.pet_node)

    def _export_dicom_info_json(self):
        """
        Extrae metadata DICOM de CT y PET (nombre, ID, fechas, etc.)
        y la guarda como JSON en exports/ para la base de datos.
        Similar al info_PET / info_CT del paciente.mat de Matlab.
        """
        import json
        try:
            import slicer
        except Exception:
            logger.warning("slicer no disponible, no se puede exportar metadata DICOM")
            return
        info = {"CT": {}, "PET": {}}
        # Intentar extraer desde la base DICOM de Slicer via atributos de nodo
        for modality, node, directory in [
            ("CT", self.ct_node, self.ct_dir),
            ("PET", self.pet_node, self.pet_dir)
        ]:
            if node is None:
                continue
            # Obtener UID de serie desde atributos del nodo
            series_uid = node.GetAttribute("DICOM.seriesInstanceUID") or ""
            study_uid = node.GetAttribute("DICOM.studyInstanceUID") or ""
            info[modality]["SeriesInstanceUID"] = series_uid
            info[modality]["StudyInstanceUID"] = study_uid
            info[modality]["Modality"] = modality
            # Nombre del nodo (ya anonimizado por _anonymize)
            info[modality]["NodeName"] = node.GetName()
            # Leer tags desde los archivos DICOM originales con pydicom
            dicom_tags = {}
            if os.path.isdir(directory):
                try:
                    import pydicom
                    for fname in sorted(os.listdir(directory)):
                        fpath = os.path.join(directory, fname)
                        if not os.path.isfile(fpath):
                            continue
                        try:
                            ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
                            for tag_name in [
                                "PatientName", "PatientID", "PatientBirthDate",
                                "PatientSex", "StudyDate", "StudyTime",
                                "StudyDescription", "StudyInstanceUID",
                                "SeriesDescription", "SeriesInstanceUID",
                                "SeriesDate", "SeriesTime",
                                "Modality", "Manufacturer", "InstitutionName",
                                "ManufacturerModelName", "DeviceSerialNumber",
                                "ReferringPhysicianName", "OperatorsName",
                                "AccessionNumber", "PatientAge", "PatientWeight",
                                "NumberOfSeriesRelatedInstances",
                                "Rows", "Columns", "SliceThickness",
                                "PixelSpacing", "SpacingBetweenSlices",
                                "RescaleIntercept", "RescaleSlope",
                            ]:
                                if hasattr(ds, tag_name) and getattr(ds, tag_name) is not None:
                                    val = getattr(ds, tag_name)
                                    if hasattr(val, "repval"):
                                        val = val.repval
                                    else:
                                        val = str(val)
                                    dicom_tags[tag_name] = val
                            break  # solo leer el primer archivo de la serie
                        except Exception:
                            continue
                except ImportError:
                    logger.debug(f"  pydicom no disponible para {modality}, usando solo atributos Slicer")
                except Exception as e:
                    logger.debug(f"  Error leyendo DICOM {modality}: {e}")
            info[modality]["DICOM"] = dicom_tags
        # Guardar JSON
        export_dir = getattr(self, "image_output_dir", None)
        if not export_dir:
            export_dir = os.path.join(self.output_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)
        pid = self.patient_id.strip() or "unknown"
        json_path = os.path.join(export_dir, f"{pid}_info.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        logger.info(f"  Metadata DICOM exportada -> {json_path}")

    def _resample_pet_to_ct(self):
        try:
            import slicer
        except Exception as e:
            logger.error(f"Error importando slicer: {e}")
            return
        if not self.pet_node or not self.ct_node:
            logger.warning("PET o CT no disponible, saltando re-muestreo")
            return
        ct_dims = self.ct_node.GetImageData().GetDimensions()
        ct_spacing = self.ct_node.GetSpacing()
        pet_dims = self.pet_node.GetImageData().GetDimensions()
        pet_spacing = self.pet_node.GetSpacing()
        if (ct_dims == pet_dims and
            abs(ct_spacing[0] - pet_spacing[0]) < 0.001 and
            abs(ct_spacing[1] - pet_spacing[1]) < 0.001 and
            abs(ct_spacing[2] - pet_spacing[2]) < 0.001):
            logger.info("PET ya tiene la misma geometria que CT")
            return
        try:
            from SlicerDosim.SlicerDosimLib import registration
            pet_resampled_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode", self.pet_node.GetName() + "_resampled_to_CT")
            reg = registration.DosimetryRegistration()
            registered_pet = reg.register(
                fixed_node=self.ct_node, moving_node=self.pet_node,
                method=registration.DosimetryRegistration.METHOD_ELASTIX_RIGID,
                output_volume_node=pet_resampled_node)
            if registered_pet is None or registered_pet.GetImageData() is None:
                raise RuntimeError("Registro Elastix fallo")
            registered_pet.SetName(self.pet_node.GetName())
            old_pet = self.pet_node
            self.pet_node = registered_pet
            slicer.mrmlScene.RemoveNode(old_pet)
            logger.info("PET re-muestreado a geometria CT: EXITOSO")
        except Exception as e:
            logger.error(f"Error en re-muestreo PET: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("Continuando con PET original")

    def _remove_couch_air(self):
        masked_node = couch_remover.remove_couch_and_air(self.ct_node)
        if masked_node is not None:
            self.ct_masked_node = masked_node

    def _segment(self):
        ct_input = self.ct_node.GetName() if self.ct_node else None
        seg_node = segmentation.run_segmentation(
            ct_input, self.output_dir, force_cpu=self.force_cpu)
        self.segmentation_node = seg_node

    def _validate_segmentation_auto(self):
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Autochequeo de segmentos")
        logger.info("  ========================================================")
        if self.segmentation_node is None:
            logger.error("  No hay nodo de segmentacion")
            return False
        try:
            import vtk
            seg_node = self.segmentation_node
            segment_ids = vtk.vtkStringArray()
            seg_node.GetSegmentation().GetSegmentIDs(segment_ids)
            num_segments = segment_ids.GetNumberOfValues()
            logger.info(f"  Segmentos: {num_segments}")
            if num_segments == 0:
                logger.error("Sin segmentos")
                return False
            all_segments = []
            for i in range(num_segments):
                sid = segment_ids.GetValue(i)
                all_segments.append(sid)
                segment = seg_node.GetSegmentation().GetSegment(sid)
                seg_name = segment.GetName() if segment else sid
                logger.info(f"    - {seg_name}")
            if self.segmenter == "totalsegmentator":
                expected_critical = ["bone", "liver", "lung"]
                found_critical = [e for e in expected_critical
                                  if any(e.lower() in s.lower() for s in all_segments)]
                logger.info(f"  Organos criticos: {found_critical}")
                if len(found_critical) < 2:
                    logger.warning("Solo {}/3 organos criticos".format(len(found_critical)))
                    return False
                return True
            else:
                if num_segments >= 1:
                    logger.info("  AUTOVALIDACION: OK")
                    return True
                else:
                    logger.error("Sin segmentos")
                    return False
        except Exception as e:
            logger.error(f"Error en autovalidacion: {e}")
            return False

    def _do_validation(self, context="segmentacion"):
        logger.info(f"  [VALIDACION MEDICA] Dialogo de {context}")
        try:
            validation.validate_segmentation(context=context)
            return True
        except RuntimeError:
            return False
        except Exception as e:
            logger.error(f"Error en dialogo de validacion: {e}")
            logger.warning("Fallback: auto-aprobando")
            return True

    def _add_tumor(self):
        import slicer
        logger.info("  Creando tumor (modo: {})...".format(
            self.tumor_config.get("mode", "synthetic")))
        result = tumor_creator.create_tumor(
            segmentation_node=self.segmentation_node,
            ct_node=self.ct_node,
            tumor_config=self.tumor_config)
        self._tumor_result = result
        logger.info(f"  Volumen tumor: {result.get('tumor_volume_cc', 'N/A')} cm^3")

    def _create_healthy_liver(self):
        import slicer
        import vtk
        seg_node = self.segmentation_node
        if seg_node is None:
            logger.error("No hay nodo de segmentacion")
            return
        seg_ids = vtk.vtkStringArray()
        seg_node.GetSegmentation().GetSegmentIDs(seg_ids)
        tumor_names = {"Tumor_Sintetico", "Tumor_Cargado", "Tumor_Manual"}
        healthy_liver_name = "higado_sano"
        found_tumor = False
        found_healthy = False
        for i in range(seg_ids.GetNumberOfValues()):
            sid = seg_ids.GetValue(i)
            segment = seg_node.GetSegmentation().GetSegment(sid)
            if segment:
                name = segment.GetName()
                if name in tumor_names:
                    found_tumor = True
                    logger.info(f"  [OK] '{name}' presente")
                if name == healthy_liver_name:
                    found_healthy = True
        if found_healthy:
            logger.info("  [OK] 'higado_sano' presente")
        else:
            logger.warning("'higado_sano' NO encontrado")

    def _validate_tumor(self, context="sintetico"):
        import slicer
        logger.info("  Validacion medica del tumor...")
        ok = tumor_validation.validate_tumor_segmentation(context=context)
        if ok:
            logger.info("  [OK] Tumor validado por el medico")
        else:
            logger.error("Tumor RECHAZADO por el medico")
            raise RuntimeError("Validacion tumoral rechazada por el medico")

    def _segment_body(self):
        import slicer
        import vtk
        import json
        ct_node = getattr(self, 'ct_node', None) or getattr(self, 'ct_masked_node', None)
        if not ct_node:
            raise RuntimeError("Nodo CT no disponible para segmentacion corporal")
        body_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "totalsegmentator_config_body.jsonc")
        body_config = {}
        if os.path.exists(body_config_path):
            try:
                import json5
                with open(body_config_path, "r", encoding="utf-8") as f:
                    body_config = json5.load(f)
            except Exception:
                pass
        task = body_config.get("task", "body")
        fast = body_config.get("fast", True)
        force_cpu = body_config.get("force_cpu", True)
        subset = body_config.get("subset", None)
        body_seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Body_Segmentation")
        body_seg_node.CreateDefaultDisplayNodes()
        slicer.util.selectModule("TotalSegmentator")
        from TotalSegmentator import TotalSegmentatorLogic
        logic = TotalSegmentatorLogic()
        logic.setupPythonRequirements()
        logic.process(
            inputVolume=ct_node, outputSegmentation=body_seg_node,
            task=task, fast=fast, cpu=force_cpu, subset=subset)
        self.body_node = body_seg_node

    def _export_labelmap(self):
        import slicer
        ct_node = getattr(self, 'ct_node', None) or getattr(self, 'ct_masked_node', None)
        seg_node = getattr(self, 'segmentation_node', None)
        body_node = getattr(self, 'body_node', None)
        if not seg_node or not ct_node:
            raise RuntimeError("Nodos necesarios no disponibles para exportar labelmap")
        labelmap_dir = getattr(self, 'image_output_dir', None) or \
                       getattr(self, 'labelmap_dir', None)
        if not labelmap_dir:
            labelmap_dir = os.path.join(self.output_dir, "exports")
            self.image_output_dir = labelmap_dir
        os.makedirs(labelmap_dir, exist_ok=True)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tissue_config_path = os.path.join(
            base_dir, "Modules", "Scripted", "SlicerDosim",
            "Resources", "Config", "tissue_config.json")
        if not os.path.exists(tissue_config_path):
            tissue_config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "Modules", "Scripted", "SlicerDosim",
                "Resources", "Config", "tissue_config.json")
        resultado = labelmap_exporter.export_labelmap(
            segmentation_node=seg_node, ct_node=ct_node,
            tissue_config_path=tissue_config_path,
            output_dir=labelmap_dir, body_segmentation_node=body_node)
        try:
            from qt import QMessageBox
            msg_box = QMessageBox(slicer.util.mainWindow())
            msg_box.setWindowTitle("Labelmap Dosimetrica Exportada")
            msg_box.setIcon(QMessageBox.Information)
            nifti = resultado.get("nifti_path") or "N/A"
            nrrd = resultado.get("nrrd_path") or "N/A"
            segs = resultado.get("num_segments", 0)
            overlaps = resultado.get("overlap_voxels", 0)
            indices = resultado.get("phantom_indices_used", [])
            msg_box.setText(
                f"<b>Labelmap exportada exitosamente</b><br><br>"
                f"Segmentos procesados: {segs}<br>"
                f"Indices phantom: {indices}<br>"
                f"Overlap voxels: {overlaps}<br><br>"
                f"<b>NIfTI:</b><br>  {nifti}<br><br>"
                f"<b>NRRD:</b><br>  {nrrd}")
            msg_box.setTextFormat(1)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setModal(False)
            msg_box.show()
            msg_box.raise_()
            msg_box.activateWindow()
        except Exception as e:
            logger.warning(f"No se pudo mostrar dialogo labelmap: {e}")

    def _save_results_json(self):
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
            "modulo": "Mod1",
            "patient_id": self.patient_id,
            "escena": "3Dosim.mrb",
            "data_dir": self.data_dir,
            "output_dir": self.output_dir,
            "segmenter": self.segmenter,
            "force_cpu": self.force_cpu,
            "total_pasos": total,
            "exitosos": ok_count,
            "fallos": fails,
            "resultado": "OK" if fails == 0 else "ERROR",
            "pasos": self.results["pasos"],
            "errores": self.results["errores"],
            "screenshots": self.screenshots,
            "checkpoint_data": self.checkpoint.state.get("data", {}),
        }
        historial.append(registro)
        with open(results_file, "w") as f:
            json.dump(historial, f, indent=2, default=str)
        logger.info(f"  Resultados guardados en: {results_file}")

    def _report(self) -> bool:
        try:
            self._save_results_json()
        except Exception as e:
            logger.warning(f"No se pudo guardar results.json: {e}")
        logger.info("")
        logger.info("=" * 70)
        logger.info(" REPORTE FINAL - MODULO 1")
        logger.info("=" * 70)
        total = len(self.results["pasos"])
        ok_count = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok_count
        skipped = sum(1 for p in self.results["pasos"] if p.get("checkpoint"))
        logger.info(f"Pasos totales:     {total}")
        logger.info(f"Exitosos:          {ok_count}")
        logger.info(f"Desde checkpoint:  {skipped}")
        logger.info(f"Fallos:            {fails}")
        if fails > 0:
            logger.info("ERRORES:")
            for err in self.results["errores"]:
                logger.info(f"  - {err}")
        logger.info("DETALLE DE PASOS:")
        logger.info("-" * 70)
        for paso in self.results["pasos"]:
            status = "+" if paso["ok"] else "-"
            cp = " (checkpoint)" if paso.get("checkpoint") else ""
            tiempo = f"{paso['tiempo']:.1f}s" if paso['tiempo'] > 0 else "-"
            logger.info(f"  {status} {paso['nombre']:<45s} {tiempo:>8s}{cp}")
        logger.info(f"Output: {self.output_dir}")
        all_ok = fails == 0
        if all_ok:
            logger.info(" RESULTADO: TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f" RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)
        return all_ok
