"""
PipelineTestOrchestrator - Orquesta el pipeline completo 3Dosim en Slicer.
Todos los imports son absolutos para compatibilidad con Slicer --python-script.
"""

import logging
import os
import time

from PipelineOrchestrator.checkpoint import CheckpointManager
from PipelineOrchestrator import anonymize
from PipelineOrchestrator import couch_remover
from PipelineOrchestrator import segmentation
from PipelineOrchestrator import validation
from PipelineOrchestrator import tumor_segmentation
from PipelineOrchestrator import tumor_validation
from PipelineOrchestrator import mcnp_builder
from PipelineOrchestrator import phantom_builder
from PipelineOrchestrator import source_builder
from PipelineOrchestrator import geometry_builder
from PipelineOrchestrator import tally_builder
from PipelineOrchestrator import git_commit
from PipelineOrchestrator.utils import logger, add_module_path, show_progress
from PipelineOrchestrator.mcp_helper import MCP
from PipelineOrchestrator.comandos import ConsolaComandos

logger = logging.getLogger("3DosimTest")


class PipelineTestOrchestrator:
    """
    Orquesta y verifica el pipeline completo 3Dosim en 3D Slicer.
    Todos los pasos tienen checkpoint: si se corta, retoma desde donde quedo.
    """

    STEP_CHECK_SLICER  = "check_slicer"
    STEP_LOAD_DICOM    = "load_dicom"
    STEP_SHOW_FUSION   = "show_fusion"
    STEP_ANONYMIZE     = "anonymize"
    STEP_REMOVE_COUCH  = "remove_couch_air"
    STEP_RESAMPLE_PET  = "resample_pet_to_ct"
    STEP_SEGMENT       = "segment_phantom"
    STEP_VALIDATE       = "validate_segmentation"
    STEP_SEGMENT_TUMOR   = "segment_tumor"
    STEP_VALIDATE_TUMOR  = "validate_tumor"
    STEP_BUILD_PHANTOM  = "build_phantom"
    STEP_BUILD_SOURCE   = "build_source"
    STEP_BUILD_GEOMETRY = "build_geometry"
    STEP_BUILD_TALLIES  = "build_tallies"
    STEP_WRITE_MCNP     = "write_mcnp"

    def __init__(self, data_dir: str, reset: bool = False, mcp_port: int = 0,
                 no_consola: bool = False, segmenter: str = "simple",
                 stop_before_segment: bool = False, force_cpu: bool = True):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")
        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")
        self.anon_dir = os.path.join(self.output_dir, ".anon")

        self.results = {"pasos": [], "errores": [], "tiempos": {}}

        self.checkpoint = CheckpointManager(self.checkpoint_dir)
        if reset:
            self.checkpoint.reset()

        self.ct_node = None
        self.ct_masked_node = None   # CT sin camilla/aire (para visualizacion)
        self.pet_node = None
        self.segmentation_node = None
        self.tumor_segmentation_node = None
        self.phantom_nifti_path = None
        self.mcnp_path = None
        self.ct_node_name = None
        self.pet_node_name = None
        self.phantom_data = None   # dict de phantom_builder.build_phantom()
        self.source_data = None    # dict de source_builder.build_source()
        self.geom_data = None      # dict de geometry_builder.build_geometry()
        self.tally_data = None     # dict de tally_builder.build_tallies()

        # MCP: servidor para que externos monitoreen + screenshots
        self.mcp = MCP()
        self.mcp_server = None
        self.mcp_port = mcp_port
        self.screenshots = []

        # Metodo de segmentacion
        self.segmenter = segmenter
        logger.info(f"  Segmentador:    {segmenter}")

        # Forzar CPU en TotalSegmentator
        self.force_cpu = force_cpu
        logger.info(f"  Force CPU:      {force_cpu}")

        # Stop antes de segmentacion (para hacer TS manual)
        self.stop_before_segment = stop_before_segment
        if stop_before_segment:
            logger.info("  Modo:           STOP antes de segmentacion (manual)")

        # Consola interactiva de comandos (habilitada por defecto)
        self.no_consola = no_consola
        self.consola = None
        if not no_consola:
            try:
                self.consola = ConsolaComandos(output_dir=self.output_dir)
            except Exception as e:
                logger.debug(f"Consola no disponible: {e}")
                self.consola = None

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Orchestrator v3.14")
        logger.info("=" * 60)
        logger.info(f"Datos:        {self.data_dir}")
        logger.info(f"Output:       {self.output_dir}")
        logger.info(f"Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info(f"Consola:      {'SI' if not no_consola else 'NO'}")
        logger.info("")

    # ==================================================================
    # RUN
    # ==================================================================

    def run(self):
        logger.info("")
        logger.info("INICIANDO PIPELINE")
        logger.info("")

        # Mostrar consola interactiva
        if self.consola:
            self.consola.log("=" * 50)
            self.consola.log(" 3Dosim Pipeline v3.14 - Consola de Comandos")
            self.consola.log(" Escribi 'ayuda' para comandos disponibles")
            self.consola.log("=" * 50)
            self.consola.log("")
            self.consola.mostrar()

        self._log_consola("Iniciando pipeline...")

        if self._checkpoint_step(self.STEP_CHECK_SLICER, "Verificando entorno Slicer",
                                 self._check_slicer,
                                 data_func=lambda: {"slicer_version": self._slicer_version()}):
            add_module_path()

        if not self._checkpoint_step(self.STEP_LOAD_DICOM, "Cargando imagenes DICOM",
                                     self._load_dicom,
                                     data_func=lambda: {"ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                                                        "pet_node_name": self.pet_node.GetName() if self.pet_node else None,
                                                        "ct_dir": self.ct_dir,
                                                        "pet_dir": self.pet_dir}):
            logger.error("Fallo critico en carga DICOM. Abortando.")
            self._report()
            return

        # Save point 1: escena Slicer comprimida post-carga DICOM
        self._save_scene("01_post_load_dicom")
        self.tomar_screenshot("01_carga_dicom")

        if not self._checkpoint_step(self.STEP_REMOVE_COUCH, "Eliminando camilla y aire",
                                     self._remove_couch_air,
                                     data_func=lambda: {"ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                                                        "ct_masked_node_name": self.ct_masked_node.GetName() if self.ct_masked_node else None}):
            logger.warning("No se pudo eliminar camilla, continuando...")
        self._save_scene("02_remove_couch")
        self.tomar_screenshot("02_remove_couch")

        if not self._checkpoint_step(self.STEP_SHOW_FUSION, "Mostrando fusion CT+PET",
                                     self._show_fusion):
            logger.warning("No se pudo mostrar fusion, continuando de todos modos")
        self._save_scene("03_fusion_ct_pet")
        self.tomar_screenshot("03_fusion_ct_pet")

        if not self._checkpoint_step(self.STEP_ANONYMIZE, "Anonimizando imagenes",
                                      self._anonymize,
                                      data_func=lambda: {"ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                                                         "pet_node_name": self.pet_node.GetName() if self.pet_node else None}):
            logger.warning("Anonimizacion fallo, continuando...")
        self._save_scene("04_anonymize")
        self.tomar_screenshot("04_anonymize")

        # Resample PET to CT geometry if PET exists
        if not self._checkpoint_step(self.STEP_RESAMPLE_PET, "Re-muestreando PET a geometria CT",
                                      self._resample_pet_to_ct,
                                      data_func=lambda: {"pet_resampled": self.pet_node is not None}):
            logger.warning("Re-muestreo PET fallo, continuando con PET original...")
        self._save_scene("05_pet_resampled")
        self.tomar_screenshot("05_pet_resampled")

        # --- STOP BEFORE SEGMENT (para hacer TS manual) ---
        if self.stop_before_segment:
            logger.info("")
            logger.info("=" * 60)
            logger.info(" PIPELINE DETENIDO ANTES DE SEGMENTACION")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Pasos completados:")
            logger.info("  1. check_slicer")
            logger.info("  2. load_dicom       → CT + PET cargados")
            logger.info("  3. remove_couch_air → camilla y aire eliminados")
            logger.info("  4. show_fusion      → fusion CT+PET lista")
            logger.info("  5. anonymize        → DICOM anonimizados")
            logger.info("")
            logger.info("Archivos generados:")
            logger.info(f"  Screenshots:  {self.output_dir}/screenshots/")
            logger.info(f"  Escena Slicer: {self.output_dir}/scenes/")
            logger.info(f"  DICOM anon:   {self.anon_dir}")
            logger.info("")
            logger.info("Para correr TotalSegmentator manual:")
            logger.info("  Desde la consola Python de Slicer:")
            logger.info("    from TotalSegmentator import TotalSegmentatorLogic")
            logger.info("    seg_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')")
            logger.info("    logic = TotalSegmentatorLogic()")
            logger.info("    logic.setupPythonRequirements()")
            logger.info("    logic.process(inputVolume=ct_node, outputSegmentation=seg_node,")
            logger.info("                  fast=True, cpu=True, task='total')")
            logger.info("")
            logger.info("  Para retomar pipeline (sin --reset):")
            logger.info("    Segmentacion manual lista → ejecutar sin --reset")
            logger.info("    El checkpoint saltara al paso 7 (validacion medica)")
            logger.info("")
            logger.info("=" * 60)

            # Guardar escena para que el usuario tenga el estado actual
            self._save_scene("01_pre_segmentacion_manual")

            # Reporte parcial
            self._log_consola("Pipeline detenido antes de segmentacion (modo manual)")
            self._report()
            return

        # --- PASO CRITICO: SEGMENTACION ---
        seg_display = f"Segmentando ({self.segmenter})"
        if self.segmenter == "totalsegmentator":
            self._log_consola("Iniciando TotalSegmentator modo rapido (5-15 min, Slicer se congelara)")
        else:
            self._log_consola("Iniciando segmentacion simple (threshold + morfologia)")
        seg_ok = self._checkpoint_step(self.STEP_SEGMENT, seg_display,
                                       self._segment,
                                       data_func=lambda: {"segmentation_node_name": self.segmentation_node.GetName() if self.segmentation_node else None,
                                                          "segmenter": self.segmenter})
        if not seg_ok:
            logger.error("")
            logger.error("=" * 60)
            logger.error(" SEGMENTACION FALLIDA. El pipeline no puede continuar.")
            logger.error(" Revise el error anterior, corrija y ejecute con --reset.")
            logger.error("=" * 60)
            self._log_consola("ERROR: Segmentacion fallida. Pipeline detenido.")
            self._report()
            return

        # Save scene + screenshot post-segmentacion
        self._save_scene("05_segmentacion")
        self.tomar_screenshot("05_segmentacion")

        # --- PASO CRITICO: VALIDACION MEDICA ---
        self._log_consola("Esperando validacion medica de la segmentacion...")
        if not self._checkpoint_step(self.STEP_VALIDATE, "Validacion medica de la segmentacion",
                                     self._do_validation,
                                     data_func=lambda: {"validado_por": "medico",
                                                        "timestamp": __import__('datetime').datetime.now().isoformat()}):
            logger.error("Validacion medica rechazada. Pipeline detenido.")
            self._log_consola("Validacion medica RECHAZADA. Pipeline detenido.")
            self._report()
            return

        # Save point 2: escena Slicer comprimida post-validacion medica
        self._save_scene("06_post_validacion")
        self.tomar_screenshot("06_validacion_medica")

        # --- PASO CRITICO: SEGMENTACION TUMORAL DESDE PET ---
        self._log_consola("Iniciando segmentacion tumoral desde PET...")
        tumor_ok = self._checkpoint_step(self.STEP_SEGMENT_TUMOR, "Segmentando tumor desde PET",
                                          self._segment_tumor,
                                          data_func=lambda: {"tumor_segmentation_node_name": self.tumor_segmentation_node.GetName() if self.tumor_segmentation_node else None})
        if not tumor_ok:
            logger.warning("Segmentacion tumoral no disponible, continuando sin tumor...")
            self._log_consola("Segmentacion tumoral no disponible, continuando...")
        else:
            self._save_scene("07_tumor_segmentation")
            self.tomar_screenshot("07_tumor_segmentation")

            # --- PASO CRITICO: VALIDACION MEDICA DEL TUMOR ---
            self._log_consola("Esperando validacion medica del tumor...")
            if not self._checkpoint_step(self.STEP_VALIDATE_TUMOR, "Validacion medica del tumor",
                                          self._validate_tumor,
                                          data_func=lambda: {"validado_por": "medico",
                                                             "timestamp": __import__('datetime').datetime.now().isoformat()}):
                logger.error("Validacion tumoral rechazada. Pipeline detenido.")
                self._log_consola("Tumor RECHAZADO por medico. Pipeline detenido.")
                self._report()
                return

            self._save_scene("08_post_validacion_tumor")
            self.tomar_screenshot("08_validacion_tumor")

        # Post-validacion: aqui se agregaran los pasos de MCNP (Modulo 2)
        # pendientes: phantom desde segmentacion, fuente desde PET,
        #            geometria voxelizada, tallies, escritura .i
        logger.info("")
        logger.info("  ╔════════════════════════════════════════════════════╗")
        logger.info("  ║   PIPELINE COMPLETO (hasta segmentacion tumoral) ║")
        logger.info("  ║                                                  ║")
        logger.info("  ║   Proximos pasos (Modulo 2 - MCNP):             ║")
        logger.info("  ║     1. Phantom desde segmentacion               ║")
        logger.info("  ║     2. Fuente desde PET                         ║")
        logger.info("  ║     3. Geometria voxelizada                     ║")
        logger.info("  ║     4. Tallies (detectores)                     ║")
        logger.info("  ║     5. Escritura archivo .i                     ║")
        logger.info("  ╚════════════════════════════════════════════════════╝")
        logger.info("")

        self._log_consola("Pipeline completado hasta segmentacion tumoral. Generando reporte...")
        ok = self._report()
        if ok:
            self._log_consola("Pipeline finalizado EXITOSAMENTE")
            git_commit.prompt_git_commit(self.data_dir)
        else:
            self._log_consola("Pipeline finalizado con ERRORES. Revise el reporte.")

    # ==================================================================
    # CHECKPOINT STEP
    # ==================================================================

    def _checkpoint_step(self, step_name, display_name, func, data_func=None):
        """Ejecuta un paso del pipeline con checkpoint.

        Si el paso ya esta completado segun checkpoint, salta.
        Si falla, registra el error y retorna False.

        Args:
            step_name: Nombre del paso (clave en checkpoint)
            display_name: Nombre visible en logs
            func: Funcion a ejecutar
            data_func: Funcion que retorna dict con datos a persistir (para BD futura)
        """
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            self._log_consola(f"[checkpoint] {display_name} — ya completado, saltando")
            # Restaurar estado desde checkpoint si hay datos
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
            # Guardar datos del paso si hay funcion extractora
            data = data_func() if data_func else {}
            self.checkpoint.mark_completed(step_name, data=data)
            show_progress(f"{display_name} completado")
            self._log_consola_ok(f"{display_name} — {elapsed:.1f}s")
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
            return False

    def _restore_step_state(self, step_name, data: dict):
        """Restaura atributos del pipeline desde checkpoint data.
        Fundamental para que al retomar desde checkpoint los nodos Slicer
        sigan siendo accesibles.
        """
        if not data:
            return
        # Mapear datos guardados a atributos del orquestador
        restore_map = {
            "ct_node": "ct_node",
            "pet_node": "pet_node",
            "segmentation_node": "segmentation_node",
            "phantom_nifti_path": "phantom_nifti_path",
            "mcnp_path": "mcnp_path",
            "ct_node_name": "ct_node_name",
            "pet_node_name": "pet_node_name",
            "ct_masked_node_name": "ct_masked_node_name",
            "tumor_segmentation_node_name": "tumor_segmentation_node_name",
        }
        for data_key, attr_name in restore_map.items():
            if data_key in data and data[data_key] is not None:
                # Si es un nombre de nodo, buscar en escena Slicer
                if data_key.endswith("_name"):
                    import slicer
                    try:
                        node = slicer.util.getNode(data[data_key])
                        # Mapear ct_node_name -> ct_node
                        actual_attr = data_key.replace("_name", "_node")
                        if hasattr(self, actual_attr):
                            setattr(self, actual_attr, node)
                    except Exception:
                        setattr(self, attr_name, data[data_key])
                else:
                    setattr(self, attr_name, data[data_key])

    # ==================================================================
    # PASOS
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

    # ==================================================================
    # MCP: servidor + screenshots
    # ==================================================================

    def _mcp_start(self):
        """Inicia el servidor MCP local si existe.

        Solo usa archivo local (slicer-mcp-server.py en el mismo directorio).
        Sin descargas de GitHub ni exec de codigo remoto.
        """
        import slicer

        mcp_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "slicer-mcp-server.py"
        )

        if os.path.exists(mcp_script):
            logger.info(f"  Iniciando MCP server desde: {mcp_script}")
            try:
                with open(mcp_script) as f:
                    code = f.read()
                exec(compile(code, mcp_script, 'exec'),
                     {"__name__": "__mcp_server__", "slicer": slicer})
                logger.info("  MCP server listo")
            except Exception as e:
                logger.warning(f"  No se pudo iniciar MCP local: {e}")
        else:
            logger.info("  MCP server no disponible (slicer-mcp-server.py no encontrado)")
            logger.info("  El pipeline seguira funcionando sin MCP externo.")

    # ==================================================================
    # CONSOLA INTERACTIVA
    # ==================================================================

    def _log_consola(self, mensaje: str):
        """Envia un mensaje a la consola interactiva (si existe)."""
        if self.consola:
            self.consola.log(mensaje)

    def _log_consola_ok(self, mensaje: str):
        """Envia un mensaje de exito a la consola."""
        if self.consola:
            self.consola.log_ok(mensaje)

    def _log_consola_error(self, mensaje: str):
        """Envia un mensaje de error a la consola."""
        if self.consola:
            self.consola.log_error(mensaje)

    def tomar_screenshot(self, nombre: str, view: str = "3D") -> "str | None":
        """Guarda un screenshot de la vista actual de Slicer.

        Args:
            nombre: Nombre identificador (ej: 'fusion', 'segmentacion')
            view: Vista a capturar ("3D", "Red", "Yellow", "Green", "all")

        Returns:
            Ruta al archivo PNG, o None si falla.
        """
        try:
            import slicer
            from datetime import datetime

            # Armar nombre de archivo
            ts = datetime.now().strftime("%H%M%S")
            filename = f"{ts}_{nombre}.png"
            filepath = os.path.join(self.output_dir, "screenshots", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Mapear vista
            view_map = {
                "3D": "vtkMRMLViewNode",
                "Red": "vtkMRMLSliceNode",
                "Yellow": "vtkMRMLSliceNode",
                "Green": "vtkMRMLSliceNode",
            }

            # Obtener el layout manager
            lm = slicer.app.layoutManager()
            if not lm:
                logger.warning(f"  No se puede tomar screenshot: sin layout manager")
                return None

            # Obtener el widget de la vista
            view_widget = None
            if view == "3D":
                view_widget = lm.threeDWidget(0).threeDView()
            elif view in ("Red", "Yellow", "Green"):
                view_widget = lm.sliceWidget(view.upper()).sliceView()

            if not view_widget:
                logger.warning(f"  Vista '{view}' no disponible para screenshot")
                return None

            # Capturar usando Qt widget.grab() (funciona en Slicer 5.x)
            pixmap = view_widget.grab()
            pixmap.save(filepath)

            self.screenshots.append(filepath)
            logger.info(f"  Screenshot: {os.path.basename(filepath)}")
            self._log_consola_ok(f"Screenshot: {nombre} ({os.path.basename(filepath)})")
            return filepath

        except Exception as e:
            logger.warning(f"  No se pudo tomar screenshot '{nombre}': {e}")
            self._log_consola_error(f"Screenshot fallo: {nombre} — {e}")
            return None

    def _save_scene(self, tag: str) -> "str | None":
        """Guarda la escena actual de Slicer en formato .mrb (comprimido).

        Args:
            tag: Identificador del save point (ej: '01_post_load_dicom')

        Returns:
            Ruta al archivo .mrb, o None si falla.
        """
        try:
            import slicer
            from datetime import datetime

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"3Dosim_scene_{tag}_{ts}.mrb"
            filepath = os.path.join(self.output_dir, "scenes", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            logger.info(f"  Guardando escena Slicer (MRB comprimido)...")
            logger.info(f"  Destino: {filepath}")

            # slicer.util.saveScene guarda en .mrb si la extension es .mrb
            success = slicer.util.saveScene(filepath)

            if success:
                logger.info(f"  Escena guardada OK: {os.path.basename(filepath)}")
                self._log_consola_ok(f"Escena guardada: {os.path.basename(filepath)}")
                return filepath
            else:
                logger.warning(f"  saveScene devolvio False")
                return None

        except Exception as e:
            logger.warning(f"  No se pudo guardar escena '{tag}': {e}")
            self._log_consola_error(f"Escena no guardada: {tag} — {e}")
            return None

    def _load_dicom(self):
        import slicer
        from DICOMLib import DICOMUtils

        for d in [self.ct_dir, self.pet_dir]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio no encontrado: {d}")

        ct_files = [f for f in os.listdir(self.ct_dir) if f.endswith('.dcm') or f.isdigit()]
        pet_files = [f for f in os.listdir(self.pet_dir) if f.endswith('.dcm') or f.isdigit()]
        logger.info(f"  Archivos CT: {len(ct_files)}")
        logger.info(f"  Archivos PET: {len(pet_files)}")

        original_db_dir = DICOMUtils.openTemporaryDatabase()
        logger.info("  DB temporal abierta")

        try:
            for dir_path, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
                logger.info(f"  Indexando {label}...")
                ok = DICOMUtils.importDicom(dir_path)
                if not ok:
                    raise RuntimeError(f"Fallo indexacion {label}")

            series_uids = DICOMUtils.allSeriesUIDsInDatabase()
            logger.info(f"  Series en DB: {len(series_uids)}")
            if not series_uids:
                raise RuntimeError("No se encontraron series DICOM")

            loaded_node_ids = DICOMUtils.loadSeriesByUID(series_uids)
            logger.info(f"  Nodos cargados: {len(loaded_node_ids)}")
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
            logger.info(f"  Nodo: {node.GetName()}")
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
            logger.warning("  PET no identificado, se usara fuente uniforme en Mod 2")

        dims = self.ct_node.GetImageData().GetDimensions()
        spacing = self.ct_node.GetSpacing()
        logger.info(f"  CT dimensiones: {dims[0]}x{dims[1]}x{dims[2]}")
        logger.info(f"  CT espaciado: {spacing[0]:.3f}x{spacing[1]:.3f}x{spacing[2]:.3f} mm")

    def _show_fusion(self):
        import slicer
        logger.info("  Configurando vista de fusion CT+PET...")

        # Forzar layout a vistas convencionales (axial/sagital/coronal + 3D)
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)

        # Asegurar display nodes para CT y PET
        ct_dn = self.ct_node.GetDisplayNode()
        if not ct_dn:
            from slicer import vtkMRMLScalarVolumeDisplayNode
            ct_dn = vtkMRMLScalarVolumeDisplayNode()
            slicer.mrmlScene.AddNode(ct_dn)
            ct_dn.SetDefaultColorMap()
            self.ct_node.SetAndObserveDisplayNodeID(ct_dn.GetID())

        # Configurar fusion (usar CT sin camilla como fondo si existe)
        bg_node = self.ct_masked_node if self.ct_masked_node else self.ct_node
        if not self.pet_node:
            logger.info("  PET no disponible, mostrando solo CT")
            slicer.util.setSliceViewerLayers(background=bg_node)
        else:
            logger.info("  Aplicando colormap Rainbow al PET...")
            # Asegurar display node para PET
            pet_dn = self.pet_node.GetDisplayNode()
            if not pet_dn:
                from slicer import vtkMRMLScalarVolumeDisplayNode
                pet_dn = vtkMRMLScalarVolumeDisplayNode()
                slicer.mrmlScene.AddNode(pet_dn)
                pet_dn.SetDefaultColorMap()
                self.pet_node.SetAndObserveDisplayNodeID(pet_dn.GetID())

            # Configurar PET con colormap Rainbow
            pet_dn.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRainbow")
            # Window/level PET basado en datos reales (p5-p95 voxels activos)
            pet_dn.AutoWindowLevelOff()
            pet_dn.SetWindowLevel(40.0, 20.0)

            # Mostrar fusion (CT sin camilla como fondo)
            slicer.util.setSliceViewerLayers(
                background=bg_node,
                foreground=self.pet_node,
                foregroundOpacity=0.35
            )

            # Ajustar window/level del CT sin camilla
            bg_dn = bg_node.GetDisplayNode()
            if bg_dn:
                bg_dn.AutoWindowLevelOff()
                bg_dn.SetWindowLevel(400.0, 40.0)

            logger.info("  Fusion CT+PET lista en vistas axial/sagital/coronal")
            logger.info("  PET: Rainbow colormap, opacidad 35%")
            logger.info("  CT: window/level ajustado para fusion")

        # Forzar refresco de vistas
        slicer.app.processEvents()
        slicer.util.resetSliceViews()
        slicer.app.processEvents()

    def _anonymize(self):
        anonymize.anonymize(self.ct_node, self.ct_dir, self.pet_dir, self.anon_dir, self.pet_node)

    def _resample_pet_to_ct(self):
        """Re-muestrea la PET a la geometria del CT usando registro previo."""
        import slicer
        from SlicerDosim.SlicerDosimLib import registration
        
        if not self.pet_node:
            logger.warning("  PET no disponible, saltando re-muestreo")
            return
            
        logger.info("  Ejecutando registro CT->PET...")
        reg = registration.DosimetryRegistration()
        
        # Registrar PET al CT (CT es fijo, PET es movil)
        try:
            # Primero aplicar registro para obtener la transformada
            registered_pet = reg.register(
                fixed_node=self.ct_node,
                moving_node=self.pet_node,
                method=registration.DosimetryRegistration.METHOD_BRAINSFIT
            )
            
            if registered_pet:
                # Reemplazar el nodo PET original con el registrado
                self.pet_node = registered_pet
                logger.info("  PET re-muestreado a geometria CT exitosamente")
            else:
                logger.warning("  Registro PET no produjo salida válida")
                
        except Exception as e:
            logger.error(f"  Error en registro PET: {e}")
            # Continuar con PET original si falla el registro
            logger.warning("  Continuando con PET original debido a error en registro")

    def _remove_couch_air(self):
        masked_node = couch_remover.remove_couch_and_air(self.ct_node)
        if masked_node is not None:
            self.ct_masked_node = masked_node

    def _segment(self):
        if self.segmenter == "totalsegmentator":
            # Pasar el NOMBRE del nodo CT en la escena (ej: "3Dosim_CT_anon")
            ct_input = self.ct_node.GetName() if self.ct_node else None
        else:
            # Simple mode: pasar el objeto nodo directamente
            ct_input = self.ct_node

        seg_node = segmentation.run_segmentation(
            ct_input, self.output_dir, mode=self.segmenter,
            force_cpu=self.force_cpu,
        )
        self.segmentation_node = seg_node

    def _do_validation(self):
        validation.validate_segmentation()

    def _segment_tumor(self):
        """
        Segmenta tumor desde PET usando SUV threshold + mascara hepatica.
        Requiere que TotalSegmentator se haya ejecutado (self.segmentation_node).
        """
        pet_node = self.pet_node
        seg_node = self.segmentation_node

        if pet_node is None:
            logger.warning("  PET no disponible, saltando segmentacion tumoral")
            return

        if seg_node is None:
            logger.warning("  Segmentacion corporal no disponible, saltando tumor")
            return

        tumor_node = tumor_segmentation.segment_tumor_from_pet(
            pet_node=pet_node,
            segmentation_node=seg_node,
            suv_threshold=2.5,
            min_volume_cc=1.0,
            segment_name="liver",
        )
        self.tumor_segmentation_node = tumor_node

    def _validate_tumor(self):
        tumor_validation.validate_tumor_segmentation()

    def _placeholder_mcnp_steps(self):
        """Placeholder para futuros pasos de MCNP.
        Se implementaran: phantom, source, geometry, tallies, writer.
        """
        logger.info("  Pasos MCNP: pendientes de implementacion")
        logger.info("  Pipeline completo hasta validacion medica.")

    # ==================================================================
    # REPORTE
    # ==================================================================

    def _save_results_json(self):
        """Guarda un archivo results.json con el resumen completo del pipeline.
        
        Este archivo sirve como registro persistente para la futura base de datos.
        """
        import json
        from datetime import datetime

        results_file = os.path.join(self.output_dir, "pipeline_results.json")
        
        # Cargar historial existente si lo hay
        historial = []
        if os.path.exists(results_file):
            try:
                with open(results_file, "r") as f:
                    historial = json.load(f)
                    if not isinstance(historial, list):
                        historial = [historial]
            except (json.JSONDecodeError, Exception):
                historial = []

        # Crear registro de esta ejecucion
        total = len(self.results["pasos"])
        ok_count = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok_count

        registro = {
            "fecha": datetime.now().isoformat(),
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
            # Datos clave recuperados del checkpoint para BD
            "checkpoint_data": self.checkpoint.state.get("data", {}),
        }

        historial.append(registro)
        
        with open(results_file, "w") as f:
            json.dump(historial, f, indent=2, default=str)
        
        logger.info(f"  Resultados guardados en: {results_file}")

    def _report(self) -> bool:
        # Guardar resultados JSON antes del reporte (para BD futura)
        try:
            self._save_results_json()
        except Exception as e:
            logger.warning(f"  No se pudo guardar results.json: {e}")

        logger.info("")
        logger.info("=" * 70)
        logger.info(" REPORTE FINAL DEL PIPELINE 3Dosim")
        logger.info("=" * 70)
        logger.info("")

        total = len(self.results["pasos"])
        ok_count = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok_count
        skipped = sum(1 for p in self.results["pasos"] if p.get("checkpoint"))

        logger.info(f"Pasos totales:     {total}")
        logger.info(f"Exitosos:          {ok_count}")
        logger.info(f"Desde checkpoint:  {skipped}")
        logger.info(f"Fallos:            {fails}")

        if fails > 0:
            logger.info("")
            logger.info("ERRORES:")
            for err in self.results["errores"]:
                logger.info(f"  - {err}")

        logger.info("")
        logger.info("DETALLE DE PASOS:")
        logger.info("-" * 70)
        for paso in self.results["pasos"]:
            status = "+" if paso["ok"] else "-"
            cp = " (checkpoint)" if paso.get("checkpoint") else ""
            tiempo = f"{paso['tiempo']:.1f}s" if paso['tiempo'] > 0 else "-"
            logger.info(f"  {status} {paso['nombre']:<45s} {tiempo:>8s}{cp}")

        logger.info("")
        logger.info("DIRECTORIOS DE SALIDA:")
        if self.phantom_nifti_path:
            logger.info(f"  Phantom NIfTI:  {self.phantom_nifti_path}")
        if self.mcnp_path:
            logger.info(f"  MCNP input:     {self.mcnp_path}")
        if self.tumor_segmentation_node:
            logger.info(f"  Tumor seg:      {self.tumor_segmentation_node.GetName()}")
        if self.screenshots:
            logger.info(f"  Screenshots:     {len(self.screenshots)} archivos")
            for s in self.screenshots:
                logger.info(f"    {os.path.basename(s)}")
        logger.info(f"  Output:         {self.output_dir}")

        logger.info("")
        logger.info("=" * 70)
        all_ok = fails == 0
        if all_ok:
            logger.info(" RESULTADO: TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f" RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)
        return all_ok
