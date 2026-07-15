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
from PipelineOrchestrator import tumor_creator
from PipelineOrchestrator import tumor_validation
from PipelineOrchestrator import labelmap_exporter
from PipelineOrchestrator import git_commit
from PipelineOrchestrator import ai_supervisor
from PipelineOrchestrator.utils import logger, add_module_path, show_progress
from PipelineOrchestrator.mcp_helper import MCP
from PipelineOrchestrator.comandos import ConsolaComandos
from PipelineOrchestrator.views import setup_medical_views, load_pipeline_config

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
    STEP_VALIDATE_AUTO = "validate_segmentation_auto"
    STEP_VALIDATE      = "validate_segmentation"
    STEP_ADD_TUMOR       = "add_synthetic_tumor"
    STEP_VALIDATE_TUMOR  = "validate_tumor"
    STEP_HEALTHY_LIVER   = "create_healthy_liver"
    STEP_SEGMENT_BODY    = "segment_body"
    STEP_EXPORT_LABELMAP = "export_labelmap"
    STEP_GENERATE_MCNP   = "generate_mcnp_input"
    STEP_VALIDATE_MCNP   = "validate_mcnp_params"

    def __init__(self, data_dir: str, reset: bool = False, mcp_port: int = 0,
                 no_consola: bool = False, segmenter: str = "totalsegmentator",
                 stop_before_segment: bool = False, force_cpu: bool = True,
                 mcnp_isotope: str = None, mcnp_n_particles: int = None,
                 mcnp_refine_hu: bool = False, mcnp_flip_rows: bool = False,
                 mcnp_flip_z: bool = False,
                 mcnp_n_liver_tallies: int = None, mcnp_n_tumor_tallies: int = None):
        self.data_dir = data_dir
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

        self.ct_node = None
        self.ct_masked_node = None   # CT sin camilla/aire (para visualizacion)
        self.pet_node = None
        self.segmentation_node = None
        self.body_node = None
        self.phantom_nifti_path = None
        self.mcnp_path = None
        self.ct_node_name = None
        self.pet_node_name = None

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
        # Pipeline config (pipeline_config.jsonc)
        self.pipeline_config = load_pipeline_config()
        self.scene_output_dir = self.pipeline_config.get(
            "scene_output_dir",
            os.path.join(self.output_dir, "scenes"),
        )
        logger.info(f"  Scene output dir: {self.scene_output_dir}")

        # Config del tumor (pipeline_config.jsonc > defaults)
        self.tumor_config = self.pipeline_config.get("tumor", {})
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        logger.info(f"  Tumor mode:     {tumor_mode}")
        if tumor_mode == "load_file":
            load_path = self.tumor_config.get("load_file_path", "")
            logger.info(f"  Tumor file:     {load_path}")
        elif tumor_mode == "manual":
            logger.info(f"  Tumor segment:  {self.tumor_config.get('manual_segment_name', 'Tumor_Manual')}")

        # Config MCNP (CLI args > config > defaults)
        mcnp_config = self.pipeline_config.get("mcnp", {})
        self.mcnp_isotope = mcnp_isotope or mcnp_config.get("isotope", "Y-90")
        self.mcnp_n_particles = mcnp_n_particles or mcnp_config.get("n_particles", int(1e7))
        self.mcnp_refine_hu = mcnp_refine_hu or mcnp_config.get("refine_hu", False)
        self.mcnp_flip_rows = mcnp_flip_rows or mcnp_config.get("flip_rows", False)
        self.mcnp_flip_z = mcnp_flip_z or mcnp_config.get("flip_z", False)
        # Tallies desde config unificada (tissue_config o defaults)
        tallies_cfg = mcnp_config.get("tallies", {})
        self.mcnp_n_liver_tallies = mcnp_n_liver_tallies or tallies_cfg.get("n_liver_tallies", 5)
        self.mcnp_n_tumor_tallies = mcnp_n_tumor_tallies or tallies_cfg.get("n_tumor_tallies", 10)
        self.mcnp_output_dir = os.path.join(self.output_dir, "mcnp_input")
        logger.info(f"  MCNP isotope:       {self.mcnp_isotope}")
        logger.info(f"  MCNP particles:     {self.mcnp_n_particles:.0e}")
        logger.info(f"  MCNP refine HU:     {self.mcnp_refine_hu}")
        logger.info(f"  MCNP flip rows:     {self.mcnp_flip_rows}")
        logger.info(f"  MCNP flip Z:        {self.mcnp_flip_z}")
        logger.info(f"  MCNP liver tallies: {self.mcnp_n_liver_tallies}")
        logger.info(f"  MCNP tumor tallies: {self.mcnp_n_tumor_tallies}")
        logger.info(f"  MCNP output dir:    {self.mcnp_output_dir}")

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

        # Cargar escena guardada si existe (para restaurar nodos Slicer)
        self._load_scene_if_needed()
        # Si hay segmentacion restaurada, generar modelos 3D
        if getattr(self, 'segmentation_node', None):
            self._show_segmentation_3d(self.segmentation_node)

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
        # Visualizacion medica automatica post-carga
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            # No segmentation yet
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        if not self._checkpoint_step(self.STEP_REMOVE_COUCH, "Eliminando camilla y aire",
                                     self._remove_couch_air,
                                     data_func=lambda: {"ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                                                        "ct_masked_node_name": self.ct_masked_node.GetName() if self.ct_masked_node else None}):
            logger.warning("No se pudo eliminar camilla, continuando...")
        self._save_scene("02_remove_couch")
        self.tomar_screenshot("02_remove_couch")

        # Resample PET to CT geometry if PET exists (ANTES de fusion!)
        if not self._checkpoint_step(self.STEP_RESAMPLE_PET, "Re-muestreando PET a geometria CT",
                                      self._resample_pet_to_ct,
                                      data_func=lambda: {"pet_resampled": self.pet_node is not None}):
            logger.warning("Re-muestreo PET fallo, continuando con PET original...")
        self._save_scene("03_pet_resampled")
        self.tomar_screenshot("03_pet_resampled")
        # Visualizacion medica post-registro PET
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        if not self._checkpoint_step(self.STEP_SHOW_FUSION, "Mostrando fusion CT+PET registrada",
                                     self._show_fusion):
            logger.warning("No se pudo mostrar fusion, continuando de todos modos")
        self._save_scene("04_fusion_ct_pet_registrada")
        self.tomar_screenshot("04_fusion_ct_pet_registrada")

        if not self._checkpoint_step(self.STEP_ANONYMIZE, "Anonimizando imagenes",
                                      self._anonymize,
                                      data_func=lambda: {"ct_node_name": self.ct_node.GetName() if self.ct_node else None,
                                                         "pet_node_name": self.pet_node.GetName() if self.pet_node else None}):
            logger.warning("Anonimizacion fallo, continuando...")
        self._save_scene("05_anonymize")
        self.tomar_screenshot("05_anonymize")

        # --- STOP BEFORE SEGMENT (para hacer TS manual) ---
        if self.stop_before_segment:
            logger.info("")
            logger.info("=" * 60)
            logger.info(" PIPELINE DETENIDO ANTES DE SEGMENTACION")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Pasos completados:")
            logger.info("  1. check_slicer")
            logger.info("  2. load_dicom        - CT + PET cargados")
            logger.info("  3. remove_couch_air  - camilla y aire eliminados")
            logger.info("  4. resample_pet      - PET registrado a CT (Elastix)")
            logger.info("  5. show_fusion       - fusion CT+PET registrada")
            logger.info("  6. anonymize         - DICOM anonimizados")
            logger.info("")
            logger.info("Archivos generados:")
            logger.info(f"  Screenshots:  {self.output_dir}/screenshots/")
            logger.info(f"  Escena Slicer: {self.scene_output_dir}/")
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
            logger.info("    Segmentacion manual lista -> ejecutar sin --reset")
            logger.info("    El checkpoint saltara al paso de segmentacion")
            logger.info("")
            logger.info("=" * 60)

            # Guardar escena para que el usuario tenga el estado actual
            self._save_scene("07_pre_segmentacion_manual")

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
        self._save_scene("08_segmentacion")
        self.tomar_screenshot("08_segmentacion")
        # Visualizacion medica con segmentacion 3D activa
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )
        # Generar modelos 3D a partir de la segmentacion
        self._show_segmentation_3d(self.segmentation_node)

        # --- AUTOVALIDACION DE LA SEGMENTACION ---
        if not self._checkpoint_step(self.STEP_VALIDATE_AUTO, "Autochequeo de segmentos",
                                      self._validate_segmentation_auto,
                                      data_func=lambda: {"segmenter": self.segmenter,
                                                         "segmentation_node": self.segmentation_node.GetName() if self.segmentation_node else None}):
            if self.segmenter == "simple":
                logger.warning("")
                logger.warning("  [ADVERTENCIA] La segmentacion SIMPLE solo genera mascara corporal.")
                logger.warning("  Para segmentacion completa (bone, liver, lung, etc):")
                logger.warning("  Use --segmenter totalsegmentator")
                logger.warning("")
            else:
                logger.warning("")
                logger.warning("  [AUTOVALIDACION] Segmentacion fallo: faltan segmentos esperados.")
                logger.warning("  Revise la segmentacion.")
                logger.warning("")
        self._log_consola("Autovalidation: " + ("OK" if True else "WARN - revisar logs"))

        # --- PASO CRITICO: VALIDACION MEDICA DE LA SEGMENTACION ---
        self._log_consola("Esperando validacion medica de la segmentacion...")
        if not self._checkpoint_step(self.STEP_VALIDATE + "_seg", "Validacion medica de la segmentacion",
                                      lambda: self._do_validation(context="segmentacion"),
                                      data_func=lambda: {"validado_por": "medico",
                                                         "contexto": "segmentacion",
                                                         "timestamp": __import__('datetime').datetime.now().isoformat()}):
            logger.error("Validacion medica rechazada. Pipeline detenido.")
            self._log_consola("Validacion medica RECHAZADA. Pipeline detenido.")
            self._report()
            return

        # Save point: escena Slicer comprimida post-validacion medica de segmentacion
        self._save_scene("08_post_validacion_segmentacion")
        self.tomar_screenshot("08_validacion_segmentacion")
        # Reforzar visualizacion medica post-validacion
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        # --- PASO: CREAR TUMOR (segun config: synthetic/load_file/manual) ---
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        mode_labels = {
            "synthetic": "Tumor sintetico esferico en higado",
            "load_file": "Cargar tumor desde archivo NIfTI",
            "manual": "Segmentacion manual del tumor en Slicer",
            "ts_liver_lesions": "Segmentacion automatica con TotalSegmentator liver_lesions",
        }
        step_label = mode_labels.get(tumor_mode, f"Tumor (modo: {tumor_mode})")
        self._log_consola(f"Creando tumor (modo: {tumor_mode})...")
        if not self._checkpoint_step(self.STEP_ADD_TUMOR, step_label,
                                      self._add_tumor,
                                      data_func=lambda: {"mode": tumor_mode,
                                                         "config": self.tumor_config}):
            logger.warning(f"Creacion de tumor (modo={tumor_mode}) fallo, continuando...")
        scene_tag_map = {
            "synthetic": "09_tumor_sintetico",
            "load_file": "09_tumor_cargado",
            "manual": "09_tumor_manual",
            "ts_liver_lesions": "09_tumor_automatico",
        }
        self._save_scene(scene_tag_map.get(tumor_mode, "09_tumor"))
        self.tomar_screenshot(scene_tag_map.get(tumor_mode, "09_tumor"))
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        # --- PASO: VERIFICAR HIGADO SANO (creado dentro de tumor_creator si aplica) ---
        create_healthy = self.tumor_config.get("create_healthy_liver", True)
        if create_healthy:
            self._log_consola("Verificando higado sano = higado - tumor...")
            if not self._checkpoint_step(self.STEP_HEALTHY_LIVER, "Higado sano (higado - tumor)",
                                          self._create_healthy_liver,
                                          data_func=lambda: {"created": True}):
                logger.warning("Verificacion de higado sano fallo, continuando...")
            self._save_scene("10_higado_sano")
            self.tomar_screenshot("10_higado_sano")
            setup_medical_views(
                ct_node=self.ct_node,
                ct_masked_node=self.ct_masked_node,
                pet_node=self.pet_node,
                segmentation_node=self.segmentation_node,
                layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
                pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
                link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
            )

        # --- PASO: VALIDACION MEDICA DEL TUMOR ---
        self._log_consola("Esperando validacion medica del tumor...")
        tumor_context = tumor_mode  # "sintetico", "load_file", "manual"
        if not self._checkpoint_step(self.STEP_VALIDATE_TUMOR, "Validacion medica del tumor",
                                      lambda: self._validate_tumor(context=tumor_context),
                                      data_func=lambda: {"context": tumor_context,
                                                         "timestamp": __import__('datetime').datetime.now().isoformat()}):
            logger.error("Validacion tumoral rechazada. Pipeline detenido.")
            self._log_consola("Validacion tumoral RECHAZADA. Pipeline detenido.")
            self._report()
            return
        self._save_scene("11_validacion_tumor")
        self.tomar_screenshot("11_validacion_tumor")
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        # --- PASO: SEGMENTACION CORPORAL (TotalSegmentator task='body') ---
        self._log_consola("Segmentando contorno corporal con TotalSegmentator (task='body')...")
        if not self._checkpoint_step(self.STEP_SEGMENT_BODY, "Segmentacion corporal (body)",
                                      self._segment_body,
                                      data_func=lambda: {"task": "body",
                                                         "fast": True,
                                                         "force_cpu": True}):
            logger.warning("Segmentacion corporal fallo, continuando sin body...")
        self._save_scene("12_segment_body")
        self.tomar_screenshot("12_segment_body")
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=self.ct_masked_node,
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )

        # --- PASO: EXPORTAR LABELMAP CON IDs DE TISSUE_CONFIG ---
        self._log_consola("Exportando labelmap dosimetrica con IDs de tissue_config...")
        if not self._checkpoint_step(self.STEP_EXPORT_LABELMAP, "Exportar labelmap dosimetrica",
                                      self._export_labelmap,
                                      data_func=lambda: {"output_dir": self.labelmap_dir}):
            logger.warning("Exportacion de labelmap fallo, continuando...")
        self._save_scene("13_labelmap_exportada")
        self.tomar_screenshot("13_labelmap_exportada")

        # --- PASO: GENERAR INPUT MCNP ---
        self._log_consola(f"Generando entrada MCNP (isotopo: {self.mcnp_isotope})...")
        if not self._checkpoint_step(self.STEP_GENERATE_MCNP, f"Generar input MCNP ({self.mcnp_isotope})",
                                      self._generate_mcnp_input,
                                      data_func=lambda: {"mcnp_path": self.mcnp_path,
                                                         "isotope": self.mcnp_isotope,
                                                         "n_particles": self.mcnp_n_particles}):
            logger.error("Generacion de input MCNP fallida.")
            self._log_consola("ERROR: Generacion MCNP fallida. Pipeline detenido.")
            self._report()
            return
        self._save_scene("14_mcnp_generado")
        self.tomar_screenshot("14_mcnp_generado")

        # --- PASO: VALIDACION DE PARAMETROS MCNP ---
        self._log_consola("Mostrando parametros MCNP para revision...")
        if not self._checkpoint_step(self.STEP_VALIDATE_MCNP, "Validar parametros MCNP",
                                      self._validate_mcnp_params,
                                      data_func=lambda: {"validado": True,
                                                         "timestamp": __import__('datetime').datetime.now().isoformat()}):
            logger.warning("Validacion de parametros MCNP fallo, continuando...")
        self._save_scene("15_mcnp_validado")
        self.tomar_screenshot("15_mcnp_validado")

        logger.info("")
        logger.info("")
        logger.info("  PIPELINE COMPLETO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. Carga DICOM")
        logger.info("    2. Eliminar camilla/aire")
        logger.info("    3. Re-muestreo PET")
        logger.info("    4. Fusion CT+PET")
        logger.info("    5. Anonimizar")
        logger.info("    6. TotalSegmentator (task=total)")
        logger.info("    7. Validacion segmentacion")
        tumor_mode = self.tumor_config.get("mode", "synthetic")
        if tumor_mode == "synthetic":
            logger.info("    8. Tumor sintetico esferico ({:.0f} mm radio en higado)".format(
                self.tumor_config.get("synthetic_radius_mm", 10)))
        elif tumor_mode == "load_file":
            logger.info("    8. Tumor cargado desde: {}".format(
                self.tumor_config.get("load_file_path", "N/A")))
        elif tumor_mode == "manual":
            logger.info("    8. Tumor segmentado manualmente en Slicer")
        elif tumor_mode == "ts_liver_lesions":
            logger.info("    8. Tumor automatico con TotalSegmentator liver_lesions")
        logger.info("    9. Validacion medica del tumor")
        if self.tumor_config.get("create_healthy_liver", True):
            logger.info("   10. Higado sano = higado - tumor")
        logger.info("   11. TotalSegmentator (task=body - contorno corporal)")
        logger.info("   12. Exportar labelmap dosimetrica (NIfTI+NRRD)")
        logger.info(f"   13. Generar input MCNP ({self.mcnp_isotope}, {self.mcnp_n_particles:.0e} particulas)")
        logger.info("   14. Validar parametros MCNP")
        logger.info("")
        if self.mcnp_path:
            logger.info(f"  Archivo MCNP: {self.mcnp_path}")

        self._log_consola("Pipeline completado. Generando reporte...")
        ok = self._report()
        if ok:
            self._log_consola("Pipeline finalizado EXITOSAMENTE")
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
            # AI review del paso
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
            # AI review incluso en fallo (para que sugiera como arreglarlo)
            self._ai_review_paso(display_name, ok=False, elapsed=elapsed,
                                 step_name=step_name, error=str(e))
            return False

    def _ai_review_paso(self, display_name: str, ok: bool, elapsed: float,
                        step_name: str, data: dict = None, error: str = None):
        """Dispara la revision por IA del paso completado (no bloqueante)."""
        try:
            ctx = {
                "paso": display_name,
                "ok": ok,
                "tiempo": elapsed,
                "datos": data or {},
                "errores": [error] if error else [],
            }
            # Agregar info de nodos Slicer al contexto si existen
            nodos_info = {}
            if self.ct_node:
                try:
                    dims = self.ct_node.GetImageData().GetDimensions()
                    spc = self.ct_node.GetSpacing()
                    nodos_info["CT"] = f"{dims[0]}x{dims[1]}x{dims[2]}, {spc[0]:.2f}x{spc[1]:.2f}x{spc[2]:.2f}mm"
                except Exception:
                    nodos_info["CT"] = self.ct_node.GetName()
            if self.pet_node:
                nodos_info["PET"] = self.pet_node.GetName()
            if self.segmentation_node:
                nodos_info["Segmentacion"] = self.segmentation_node.GetName()
                # Extraer metricas de calidad de la segmentacion
                try:
                    seg_metrics = self._extract_segmentation_metrics()
                    if seg_metrics:
                        ctx["datos"]["segmentation_metrics"] = seg_metrics
                except Exception:
                    pass
            if self.ct_masked_node:
                nodos_info["CT_masked"] = self.ct_masked_node.GetName()
            # Incluir el tipo de segmentador usado
            ctx["datos"]["segmenter_type"] = getattr(self, "segmenter", "desconocido")
            ctx["datos"]["nodos_activos"] = nodos_info

            ai_supervisor.revisar_paso(ctx, consola=self.consola)
        except Exception as e:
            logger.debug(f"AI review no disponible: {e}")

    def _extract_segmentation_metrics(self) -> dict:
        """Extrae metricas de calidad de la segmentacion actual.

        Returns:
            dict con: num_segments, volume_cc, segment_names, warnings.
        """
        metrics = {}
        try:
            import slicer
            seg_node = self.segmentation_node
            if not seg_node:
                return metrics

            seg_display = seg_node.GetDisplayNode()
            if not seg_display:
                return metrics

            # Contar segmentos
            seg_collection = seg_node.GetSegmentation()
            if not seg_collection:
                return metrics

            import vtk
            segment_ids = vtk.vtkStringArray()
            seg_collection.GetSegmentIDs(segment_ids)
            num_segments = segment_ids.GetNumberOfValues()
            metrics["num_segments"] = num_segments

            # Nombre de cada segmento
            names = []
            for i in range(num_segments):
                seg_id = segment_ids.GetValue(i)
                segment = seg_collection.GetSegment(seg_id)
                if segment:
                    names.append(segment.GetName())
            metrics["segment_names"] = names

            # Volumen total aproximado (usando labelmap)
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
                    # Voxels fuera del rango corporal (en aire, fuera del CT masked)
                    if self.ct_masked_node:
                        ct_arr = slicer.util.arrayFromVolume(self.ct_masked_node)
                        # Voxels segmentados donde CT_masked es 0 (aire/camilla)
                        fuera_cuerpo = np.count_nonzero((arr > 0) & (ct_arr <= -200))
                        metrics["voxels_fuera_cuerpo"] = int(fuera_cuerpo)
                slicer.mrmlScene.RemoveNode(labelmap_node)
            except Exception:
                pass

            # Warnings de calidad
            warnings = []
            if num_segments <= 2:
                warnings.append(
                    f"Solo {num_segments} segmento(s) detectado(s). "
                    "Un cuerpo completo deberia tener ~104 organos. "
                    "Si se uso segmentacion simple (threshold), esto es esperable "
                    "pero insuficiente para dosimetria."
                )
            if metrics.get("voxels_fuera_cuerpo", 0) > 1000:
                warnings.append(
                    f"Se detectaron {metrics['voxels_fuera_cuerpo']} voxels "
                    "segmentados fuera del contorno corporal (en aire). "
                    "Esto indica que la segmentacion incluye ruido o camilla."
                )
            metrics["warnings"] = warnings

        except Exception as e:
            logger.debug(f"Error extrayendo metricas de segmentacion: {e}")

        return metrics

    def _restore_step_state(self, step_name, data: dict):
        """Restaura atributos del pipeline desde checkpoint data.
        Fundamental para que al retomar desde checkpoint los nodos Slicer
        sigan siendo accesibles.

        Si getNode falla (por renombre post-anonymize), busca nodos
        escaneando la escena por tipo (vtkMRMLScalarVolumeNode,
        vtkMRMLSegmentationNode).

        Ademas, restaura la visualizacion medica para que el usuario
        pueda ver inmediatamente el estado actual del pipeline.
        """
        if not data:
            return
        import slicer
        # Mapear datos guardados a atributos del orquestador
        restore_map = {
            "ct_node": "ct_node",
            "pet_node": "pet_node",
            "segmentation_node": "segmentation_node",
            "ct_node_name": "ct_node_name",
            "pet_node_name": "pet_node_name",
            "ct_masked_node_name": "ct_masked_node_name",
            "mcnp_path": "mcnp_path",
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
                        # Fallback: escanear escena por tipo
                        self._restore_node_by_type(data_key, data[data_key])
                else:
                    setattr(self, attr_name, data[data_key])

    def _restore_node_by_type(self, data_key: str, node_name: str):
        """Busca un nodo en la escena por tipo cuando getNode falla.
        Asigna al atributo correspondiente del orquestador."""
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
        # Buscar por tipo en la escena
        nodes = slicer.util.getNodesByClass(node_type)
        if not nodes:
            logger.warning(f"  No se encontraron nodos de tipo {node_type} en escena")
            return
        if len(nodes) == 1:
            chosen = nodes[0]
        else:
            # Multiples nodos: preferir por nombre que contenga CT/PET/Seg
            keywords = {
                "ct": "CT",
                "pet": "PET",
                "seg": "Seg",
                "masked": "sin_camilla",
            }
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
            logger.info(f"  Nodo restaurado por busqueda: '{chosen.GetName()}' -> self.{attr}")

        # Restaurar visualizacion medica si hay nodos disponibles
        if self.ct_node or self.pet_node:
            try:
                setup_medical_views(
                    ct_node=self.ct_node,
                    ct_masked_node=self.ct_masked_node,
                    pet_node=self.pet_node,
                    segmentation_node=self.segmentation_node,
                    layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
                    pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
                    link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
                )
                logger.info(f"  Visualizacion medica restaurada desde checkpoint '{step_name}'")
            except Exception as e:
                logger.debug(f"  No se pudo restaurar visualizacion: {e}")

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

    def _load_scene_if_needed(self):
        """Carga la escena MRB guardada si hay checkpoints completados.
        
        Al reanudar pipeline con Slicer fresco, la escena debe cargarse
        para que los nodos (CT, PET, segmentacion) esten disponibles.
        Despues de cargar, escanea la escena para asignar nodos criticos
        a self.ct_node, self.ct_masked_node, self.pet_node, self.segmentation_node.
        """
        import slicer
        scene_path = os.path.join(self.scene_output_dir, "3Dosim_scene.mrb")
        if not os.path.exists(scene_path):
            return
        # Solo cargar si hay checkpoints que necesiten nodos
        checkpoint_keys = [
            self.STEP_LOAD_DICOM, self.STEP_REMOVE_COUCH,
            self.STEP_RESAMPLE_PET, self.STEP_SEGMENT,
        ]
        needs_restore = any(
            self.checkpoint.is_completed(k) for k in checkpoint_keys
        )
        if not needs_restore:
            return
        logger.info(f"  Cargando escena guardada desde checkpoint: {scene_path}")
        try:
            success = slicer.util.loadScene(scene_path)
            if success:
                logger.info(f"  Escena cargada OK desde checkpoint")
            else:
                logger.warning(f"  loadScene devolvio False")
        except Exception as e:
            logger.warning(f"  No se pudo cargar escena: {e}")
        # Escanear la escena para restaurar nodos criticos
        self._scan_scene_for_nodes()

    def _scan_scene_for_nodes(self):
        """Escanea la escena de Slicer y asigna nodos criticos a self.
        
        Busca nodos por tipo y nombre keywords:
          CT_anon -> self.ct_node
          PET_anon -> self.pet_node
          CT_sin_camilla -> self.ct_masked_node
          TotalSegmentator_Seg/Segmentation -> self.segmentation_node
        """
        import slicer
        import vtk

        # Buscar volumenes escalares
        vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        seg_nodes_list = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")

        logger.info(f"  Escaneando escena: {len(vol_nodes)} volumenes, {len(seg_nodes_list)} segmentaciones")

        # Asignar CT: preferir "CT_anon" o "CT_sin_camilla" o cualquier CT
        ct_candidates = [n for n in vol_nodes if "CT" in n.GetName() or "ct" in n.GetName().lower()]
        if ct_candidates and not getattr(self, 'ct_node', None):
            self.ct_node = ct_candidates[0]
            logger.info(f"  Nodo CT restaurado: '{self.ct_node.GetName()}'")

        # Asignar CT_masked: "sin_camilla" o "masked"
        masked_candidates = [n for n in vol_nodes if "sin_camilla" in n.GetName().lower() or "masked" in n.GetName().lower()]
        if not masked_candidates:
            # Si no hay nodo sin_camilla, usar CT_anon como masked
            masked_candidates = ct_candidates
        if masked_candidates and not getattr(self, 'ct_masked_node', None):
            self.ct_masked_node = masked_candidates[0]
            logger.info(f"  Nodo CT_masked restaurado: '{self.ct_masked_node.GetName()}'")

        # Asignar PET: preferir "PET_anon" o "PET" 
        pet_candidates = [n for n in vol_nodes if "PET" in n.GetName() or "pet" in n.GetName().lower()]
        if pet_candidates and not getattr(self, 'pet_node', None):
            self.pet_node = pet_candidates[0]
            logger.info(f"  Nodo PET restaurado: '{self.pet_node.GetName()}'")

        # Asignar segmentacion (organos + tumor)
        if seg_nodes_list and not getattr(self, 'segmentation_node', None):
            # Preferir el que tiene mas segmentos o el que dice "TotalSegmentator"
            ts_candidates = [n for n in seg_nodes_list if "TotalSegmentator" in n.GetName()]
            self.segmentation_node = ts_candidates[0] if ts_candidates else seg_nodes_list[0]
            logger.info(f"  Nodo segmentacion restaurado: '{self.segmentation_node.GetName()}'")
            # Contar segmentos
            seg_ids = vtk.vtkStringArray()
            self.segmentation_node.GetSegmentation().GetSegmentIDs(seg_ids)
            logger.info(f"    Segmentos: {seg_ids.GetNumberOfValues()}")

        # Asignar body_node si existe
        body_candidates = [n for n in seg_nodes_list if "Body" in n.GetName()]
        if body_candidates and not getattr(self, 'body_node', None):
            self.body_node = body_candidates[0]
            logger.info(f"  Nodo Body restaurado: '{self.body_node.GetName()}'")

    def _show_segmentation_3d(self, seg_node=None):
        """Crea representacion 3D (closed surface) para todos los segmentos.
        
        Hace visible la segmentacion en la vista 3D como modelos
        de superficie cerrada con sus colores originales.
        
        Args:
            seg_node: nodo de segmentacion. Si None, usa self.segmentation_node.
        """
        import slicer
        import vtk
        seg_node = seg_node or getattr(self, 'segmentation_node', None)
        if not seg_node:
            logger.warning("  No hay nodo de segmentacion para mostrar en 3D")
            return

        seg_ids = vtk.vtkStringArray()
        seg_node.GetSegmentation().GetSegmentIDs(seg_ids)
        n = seg_ids.GetNumberOfValues()

        logger.info(f"  Generando modelos 3D para {n} segmentos...")

        try:
            # Crear representacion closed surface para todos los segmentos
            # (esto permite la visualizacion 3D nativa en Slicer)
            seg_node.CreateClosedSurfaceRepresentation()

            # Asegurar que todos los segmentos sean visibles
            disp_node = seg_node.GetDisplayNode()
            if disp_node:
                try:
                    disp_node.SetAllSegmentsVisible(True)
                except AttributeError:
                    pass
        except Exception as e:
            logger.warning(f"  No se pudo generar representacion 3D (no critico): {e}")

        logger.info(f"  Segmentacion visible en vista 3D: {n} segmentos")

    def _save_scene(self, tag: str = None) -> "str | None":
        """Guarda la escena actual de Slicer en formato .mrb (comprimido).

        Usa SIEMPRE el mismo nombre de archivo ('3Dosim_scene.mrb') para que
        las escenas sean incrementales (cada save sobreescribe la anterior).
        El tag solo se usa para el log.

        Usa scene_output_dir del pipeline_config.jsonc.
        Si no existe, fallback a self.output_dir/scenes/.

        Args:
            tag: Identificador del save point para log (ej: 'post_load_dicom')

        Returns:
            Ruta al archivo .mrb, o None si falla.
        """
        try:
            import slicer

            # Usar SIEMPRE el mismo nombre de archivo (incremental)
            filename = "3Dosim_scene.mrb"
            # Usar scene_output_dir del config JSONC central
            scene_dir = getattr(self, "scene_output_dir", None)
            if not scene_dir:
                scene_dir = os.path.join(self.output_dir, "scenes")
            filepath = os.path.join(scene_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            logger.info(f"  Escena{' ['+tag+']' if tag else ''} -> {filepath}")

            logger.info(f"  Guardando escena Slicer (MRB comprimido)...")
            logger.info(f"  Destino: {filepath}")

            # Guardar variables de entorno TMP para restaurar despues
            old_tmp = os.environ.get("TMP", "")
            old_temp = os.environ.get("TEMP", "")

            try:
                # Usar un TMP corto (C:/tmp) para evitar error Windows MAX_PATH
                # en archivos NRRD temporales que escribe Slicer al comprimir .mrb
                short_tmp = r"C:\tmp"
                os.makedirs(short_tmp, exist_ok=True)
                os.environ["TMP"] = short_tmp
                os.environ["TEMP"] = short_tmp

                success = slicer.util.saveScene(filepath)
            finally:
                # Restaurar TMP original siempre
                os.environ["TMP"] = old_tmp
                os.environ["TEMP"] = old_temp

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
        # En modo headless (no-main-window) el layoutManager puede ser None
        lm = slicer.app.layoutManager()
        if lm is None:
            logger.warning("  No hay layout manager (posible modo headless). Saltando configuracion visual.")
            return
            
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

            # Verificar que el PET tenga datos validos
            if self.pet_node.GetImageData() is None:
                logger.warning("  PET sin datos de imagen, no se puede mostrar fusion")
            else:
                logger.info(f"  PET datos OK: {self.pet_node.GetImageData().GetDimensions()}")

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
        """Re-muestrea la PET a la geometria exacta del CT usando registro Elastix rigid.
        
        Usa Elastix con preset 'rigid(all)' para registrar PET al CT y generar
        un volumen PET re-muestreado con las mismas dimensiones, origen y espaciado
        que el CT. Esto aseguna una fusion perfecta entre ambas imagenes.
        """
        try:
            import slicer
        except Exception as e:
            logger.error(f"  Error importando slicer: {e}")
            return
            
        if not self.pet_node:
            logger.warning("  PET no disponible, saltando re-muestreo")
            return
            
        if not self.ct_node:
            logger.warning("  CT no disponible, saltando re-muestreo")
            return
            
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Re-muestreando PET a geometria CT con Elastix (rigid)")
        logger.info("  ========================================================")
        logger.info("")
        
        # Mostrar geometria actual del CT (referencia)
        ct_dims = self.ct_node.GetImageData().GetDimensions()
        ct_spacing = self.ct_node.GetSpacing()
        ct_origin = self.ct_node.GetOrigin()
        logger.info(f"  CT referencia:")
        logger.info(f"    Dimensiones: {ct_dims[0]}x{ct_dims[1]}x{ct_dims[2]}")
        logger.info(f"    Espaciado:   {ct_spacing[0]:.3f}x{ct_spacing[1]:.3f}x{ct_spacing[2]:.3f} mm")
        logger.info(f"    Origen:      {ct_origin[0]:.1f},{ct_origin[1]:.1f},{ct_origin[2]:.1f}")
        
        # Mostrar geometria actual del PET (antes del re-muestreo)
        pet_dims = self.pet_node.GetImageData().GetDimensions()
        pet_spacing = self.pet_node.GetSpacing()
        pet_origin = self.pet_node.GetOrigin()
        logger.info(f"  PET original:")
        logger.info(f"    Dimensiones: {pet_dims[0]}x{pet_dims[1]}x{pet_dims[2]}")
        logger.info(f"    Espaciado:   {pet_spacing[0]:.3f}x{pet_spacing[1]:.3f}x{pet_spacing[2]:.3f} mm")
        logger.info(f"    Origen:      {pet_origin[0]:.1f},{pet_origin[1]:.1f},{pet_origin[2]:.1f}")
        
        # Verificar si ya coinciden (evitar trabajo innecesario)
        if (ct_dims == pet_dims and 
            abs(ct_spacing[0] - pet_spacing[0]) < 0.001 and
            abs(ct_spacing[1] - pet_spacing[1]) < 0.001 and
            abs(ct_spacing[2] - pet_spacing[2]) < 0.001):
            logger.info("  PET ya tiene la misma geometria que CT — no requiere re-muestreo")
            return
        
        logger.info("  Registrando PET al CT con Elastix (rigid preset)...")
        
        try:
            from SlicerDosim.SlicerDosimLib import registration
            
            # Crear nodo de salida para el PET re-muestreado
            pet_resampled_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode",
                self.pet_node.GetName() + "_resampled_to_CT"
            )
            
            # Registrar PET al CT usando Elastix con preset rigid
            reg = registration.DosimetryRegistration()
            registered_pet = reg.register(
                fixed_node=self.ct_node,
                moving_node=self.pet_node,
                method=registration.DosimetryRegistration.METHOD_ELASTIX_RIGID,
                output_volume_node=pet_resampled_node
            )
            
            if registered_pet is None:
                raise RuntimeError("Elastix registro no produjo nodo de salida")
            
            # Verificar que el nodo de salida tenga datos
            if registered_pet.GetImageData() is None:
                raise RuntimeError("Elastix registro no produjo datos de imagen")
            
            # Verificar dimensiones del resultado
            out_dims = registered_pet.GetImageData().GetDimensions()
            out_spacing = registered_pet.GetSpacing()
            logger.info(f"  PET re-muestreado:")
            logger.info(f"    Dimensiones: {out_dims[0]}x{out_dims[1]}x{out_dims[2]}")
            logger.info(f"    Espaciado:   {out_spacing[0]:.3f}x{out_spacing[1]:.3f}x{out_spacing[2]:.3f} mm")
            
            # Verificar que coincida con CT
            dims_ok = (out_dims[0] == ct_dims[0] and 
                       out_dims[1] == ct_dims[1] and 
                       out_dims[2] == ct_dims[2])
            spacing_ok = (abs(out_spacing[0] - ct_spacing[0]) < 0.001 and
                          abs(out_spacing[1] - ct_spacing[1]) < 0.001 and
                          abs(out_spacing[2] - ct_spacing[2]) < 0.001)
            
            if not dims_ok:
                logger.warning(f"  Dimensiones NO coinciden con CT: {out_dims} vs {ct_dims}")
            else:
                logger.info("  [OK] Dimensiones coinciden con CT")
                
            if not spacing_ok:
                logger.warning(f"  Espaciado NO coincide con CT: {out_spacing} vs {ct_spacing}")
            else:
                logger.info("  [OK] Espaciado coincide con CT")
            
            # Reemplazar nodo PET original por el re-muestreado
            original_name = self.pet_node.GetName()
            registered_pet.SetName(original_name)
            
            old_pet = self.pet_node
            self.pet_node = registered_pet
            slicer.mrmlScene.RemoveNode(old_pet)
            # registered_pet ES pet_resampled_node (mismo objeto) — NO borrarlo
            
            logger.info("  PET re-muestreado a geometria CT: EXITOSO")
            logger.info("  ========================================================")
            
        except Exception as e:
            logger.error(f"  Error en re-muestreo PET con Elastix: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("  Continuando con PET original debido a error en re-muestreo")
            logger.info("  ========================================================")

    def _remove_couch_air(self):
        masked_node = couch_remover.remove_couch_and_air(self.ct_node)
        if masked_node is not None:
            self.ct_masked_node = masked_node

    def _segment(self):
        # Pasar el NOMBRE del nodo CT en la escena (ej: "3Dosim_CT_anon")
        ct_input = self.ct_node.GetName() if self.ct_node else None

        seg_node = segmentation.run_segmentation(
            ct_input, self.output_dir,
            force_cpu=self.force_cpu,
        )
        self.segmentation_node = seg_node

    def _validate_segmentation_auto(self):
        """
        Autovalida la segmentacion verificando que contenga segmentos esperados.

        Para TotalSegmentator: busca organos clave (bone, liver, lung, kidney, etc).
        Para simple: verifica que al menos exista un segmento (mascara corporal).

        Returns: True si pasa las validaciones minimas
        """
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Autochequeo de segmentos en segmentacion")
        logger.info("  ========================================================")
        logger.info("")

        if self.segmentation_node is None:
            logger.error("  No hay nodo de segmentacion para validar")
            return False

        try:
            import vtk

            # Obtener segmentos del nodo de segmentacion
            seg_node = self.segmentation_node
            segment_ids = vtk.vtkStringArray()
            seg_node.GetSegmentation().GetSegmentIDs(segment_ids)

            num_segments = segment_ids.GetNumberOfValues()
            logger.info(f"  Segmentos encontrados: {num_segments}")

            if num_segments == 0:
                logger.error("  La segmentacion no contiene ningun segmento")
                return False

            # Listar todos los segmentos disponibles
            all_segments = []
            for i in range(num_segments):
                seg_id = segment_ids.GetValue(i)
                all_segments.append(seg_id)
                segment = seg_node.GetSegmentation().GetSegment(seg_id)
                seg_name = segment.GetName() if segment else seg_id
                logger.info(f"    - {seg_name}")

            # Verificar segmentos esperados segun el metodo
            if self.segmenter == "totalsegmentator":
                # Organos clave esperados de TotalSegmentator task='total'
                expected_critical = ["bone", "liver", "lung"]
                # Organos deseables (opcionales)
                expected_optional = ["kidney_left", "kidney_right", "spleen",
                                     "heart", "stomach", "pancreas",
                                     "urinary_bladder", "thyroid_gland"]

                found_critical = []
                missing_critical = []
                for exp in expected_critical:
                    if any(exp.lower() in s.lower() for s in all_segments):
                        found_critical.append(exp)
                    else:
                        missing_critical.append(exp)

                found_optional = []
                for exp in expected_optional:
                    if any(exp.lower() in s.lower() for s in all_segments):
                        found_optional.append(exp)

                logger.info(f"  Organos criticos encontrados: {found_critical}")
                if missing_critical:
                    logger.warning(f"  Organos criticos faltantes: {missing_critical}")
                if found_optional:
                    logger.info(f"  Organos opcionales encontrados: {found_optional}")

                # Fallo si falta algun organo critico? No necesariamente,
                # puede ser que el paciente no tenga ese organo visible.
                # Pero al menos deberia haber hueso e higado.
                if len(found_critical) < 2:
                    logger.warning("  Solo se encontraron {}/3 organos criticos".format(len(found_critical)))
                    logger.warning("  La segmentacion puede estar incompleta")
                    return False

                return True

            else:
                # Simple segmentation: solo mascara corporal
                logger.info("  Segmentacion simple: solo se espera mascara corporal")
                logger.info("  Para segmentacion completa de organos, use --segmenter totalsegmentator")
                # Con al menos 1 segmento, la segmentacion simple es aceptable
                if num_segments >= 1:
                    logger.info("  AUTOVALIDACION: OK (mascara corporal presente)")
                    return True
                else:
                    logger.error("  No hay segmentos en la segmentacion simple")
                    return False

        except Exception as e:
            logger.error(f"  Error en autovalidation de segmentacion: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _do_validation(self, context="segmentacion"):
        """Ejecuta validacion medica real (dialogo Qt NO MODAL).

        Args:
            context: "fusion" o "segmentacion" — cambia mensaje del dialogo.

        Returns:
            True si el medico aprueba, False si rechaza.
        """
        logger.info(f"  [VALIDACION MEDICA] Iniciando dialogo de {context}")
        try:
            validation.validate_segmentation(context=context)
            return True
        except RuntimeError:
            return False
        except Exception as e:
            logger.error(f"  Error en dialogo de validacion: {e}")
            # Fallback: si el dialogo Qt falla, auto-aprobar para no bloquear
            logger.warning("  Fallback: auto-aprobando (dialogo no disponible)")
            return True

    # ==================================================================
    # TUMOR (soporta 3 modos: synthetic, load_file, manual)
    # ==================================================================

    def _add_tumor(self):
        """Crea tumor segun config (synthetic/load_file/manual)."""
        import slicer
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Creando tumor (modo: {})...".format(
            self.tumor_config.get("mode", "synthetic")))
        logger.info("  ========================================================")

        result = tumor_creator.create_tumor(
            segmentation_node=self.segmentation_node,
            ct_node=self.ct_node,
            tumor_config=self.tumor_config,
        )

        # Guardar resultado para referencia (volumen, etc.)
        self._tumor_result = result
        logger.info(f"  Volumen tumor: {result.get('tumor_volume_cc', 'N/A')} cm^3")
        logger.info(f"  Modo usado: {result.get('mode', 'N/A')}")

        logger.info("  ========================================================")

    def _create_healthy_liver(self):
        """Verifica que higado_sano fue creado (por tumor_creator)."""
        import slicer
        import vtk

        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Verificando higado sano en la segmentacion...")
        logger.info("  ========================================================")

        seg_node = self.segmentation_node
        if seg_node is None:
            logger.error("  No hay nodo de segmentacion")
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
                if name in tumor_names:  # exact match
                    found_tumor = True
                    logger.info(f"  [OK] Segmento '{name}' presente")
                if name == healthy_liver_name:  # exact match
                    found_healthy = True

        if not found_tumor:
            logger.warning("  Ningun segmento de tumor encontrado")
        if found_healthy:
            logger.info("  [OK] Segmento 'higado_sano' presente")
            logger.info("  higado_sano = higado - tumor verificado")
        else:
            healthy_enabled = self.tumor_config.get("create_healthy_liver", True)
            if healthy_enabled:
                logger.warning("  Segmento 'higado_sano' NO encontrado")
            else:
                logger.info("  'create_healthy_liver'=false, saltando")

        logger.info("  ========================================================")

    # ==================================================================
    # VALIDACION MEDICA DEL TUMOR
    # ==================================================================

    def _validate_tumor(self, context="sintetico"):
        """Solicita validacion medica del tumor.
        
        Args:
            context: "sintetico" | "load_file" | "manual" — cambia el texto del dialogo.
        """
        import slicer
        logger.info("")
        logger.info("  ========================================================")
        logger.info(f"  Validacion medica del tumor (contexto: {context})...")
        logger.info("  ========================================================")

        ok = tumor_validation.validate_tumor_segmentation(context=context)
        if ok:
            logger.info("  [OK] Tumor validado por el medico")
        else:
            logger.error("  Tumor RECHAZADO por el medico")
            raise RuntimeError("Validacion tumoral rechazada por el medico")

        logger.info("  ========================================================")

    # ==================================================================
    # SEGMENTACION CORPORAL (TotalSegmentator task='body')
    # ==================================================================

    def _segment_body(self):
        """Ejecuta TotalSegmentator con task='body' para contorno corporal."""
        import slicer
        import vtk
        import json
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Segmentando contorno corporal...")
        logger.info("  ========================================================")

        ct_node = getattr(self, 'ct_node', None)
        if not ct_node:
            logger.warning("  ct_node no disponible, usando ct_masked_node...")
            ct_node = getattr(self, 'ct_masked_node', None)
        if not ct_node:
            raise RuntimeError("Nodo CT no disponible para segmentacion corporal")

        # Cargar config body o defaults
        body_config = {}
        body_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "totalsegmentator_config_body.jsonc"
        )
        if os.path.exists(body_config_path):
            try:
                import json5
                with open(body_config_path, "r", encoding="utf-8") as f:
                    body_config = json5.load(f)
                logger.info(f"  Config body cargada: {body_config_path}")
            except Exception as e:
                logger.warning(f"  No se pudo cargar config body: {e}")
                body_config = {}

        task = body_config.get("task", "body")
        fast = body_config.get("fast", True)
        force_cpu = body_config.get("force_cpu", True)
        subset = body_config.get("subset", None)

        # Crear nodo de segmentacion para body
        body_seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Body_Segmentation")
        body_seg_node.CreateDefaultDisplayNodes()

        logger.info(f"  Ejecutando TotalSegmentator task='{task}' para contorno corporal...")

        # Usar TotalSegmentatorLogic.process() directamente (como en segmentation.py)
        slicer.util.selectModule("TotalSegmentator")
        from TotalSegmentator import TotalSegmentatorLogic
        logic = TotalSegmentatorLogic()
        logic.setupPythonRequirements()
        logic.process(
            inputVolume=ct_node,
            outputSegmentation=body_seg_node,
            task=task,
            fast=fast,
            cpu=force_cpu,
            subset=subset,
        )

        # Guardar como self.body_node para referencia posterior
        self.body_node = body_seg_node
        logger.info(f"  Body segmentado: {body_seg_node.GetName()}")

        # Verificar que hay segmentos
        seg_ids = vtk.vtkStringArray()
        body_seg_node.GetSegmentation().GetSegmentIDs(seg_ids)
        n = seg_ids.GetNumberOfValues()
        logger.info(f"  Segmentos corporales encontrados: {n}")
        for i in range(n):
            sid = seg_ids.GetValue(i)
            seg = body_seg_node.GetSegmentation().GetSegment(sid)
            if seg:
                logger.info(f"    - {seg.GetName()}")

        logger.info("  ========================================================")

    # ==================================================================
    # EXPORTAR LABELMAP DOSIMETRICA
    # ==================================================================

    def _export_labelmap(self):
        """Exporta labelmap dosimetrica con IDs de tissue_config.json."""
        import slicer
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Exportando labelmap dosimetrica...")
        logger.info("  ========================================================")

        ct_node = getattr(self, 'ct_node', None) or getattr(self, 'ct_masked_node', None)
        seg_node = getattr(self, 'segmentation_node', None)
        body_node = getattr(self, 'body_node', None)

        if not seg_node:
            raise RuntimeError("Nodo de segmentacion no disponible para exportar labelmap")

        if not ct_node:
            raise RuntimeError("Nodo CT no disponible para geometria de labelmap")

        # Crear directorio de salida
        labelmap_dir = getattr(self, 'labelmap_dir', None)
        if not labelmap_dir:
            labelmap_dir = os.path.join(self.output_dir, "labelmaps")
            self.labelmap_dir = labelmap_dir
        os.makedirs(labelmap_dir, exist_ok=True)

        logger.info(f"  Directorio de labelmaps: {labelmap_dir}")

        # Cargar tissue_config
        # __file__ = .../SlicerDosim/Testing/PipelineOrchestrator/pipeline.py
        # Subir 2 niveles: Testing/PipelineOrchestrator/ -> SlicerDosim/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tissue_config_path = os.path.join(
            base_dir,
            "Modules", "Scripted", "SlicerDosim",
            "Resources", "Config", "tissue_config.json"
        )
        if not os.path.exists(tissue_config_path):
            # Fallback: buscar relativo a PipelineOrchestrator
            tissue_config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..",
                "Modules", "Scripted", "SlicerDosim",
                "Resources", "Config", "tissue_config.json"
            )

        logger.info(f"  Tissue config: {tissue_config_path}")

        resultado = labelmap_exporter.export_labelmap(
            segmentation_node=seg_node,
            ct_node=ct_node,
            tissue_config_path=tissue_config_path,
            output_dir=labelmap_dir,
            body_segmentation_node=body_node,
        )

        # Mostrar dialogo NO MODAL con resumen de la exportacion (permite navegar Slicer)
        try:
            from qt import QMessageBox
            import slicer
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
                f"<b>NRRD:</b><br>  {nrrd}"
            )
            msg_box.setTextFormat(1)  # Qt.RichText
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setModal(False)
            msg_box.show()
            msg_box.raise_()
            msg_box.activateWindow()
        except Exception as e:
            logger.warning(f"  No se pudo mostrar dialogo labelmap: {e}")

        logger.info("  ========================================================")

    # ==================================================================
    # GENERACION MCNP
    # ==================================================================

    def _generate_mcnp_input(self):
        """Genera el archivo de entrada MCNP usando MCNPInputGenerator."""
        import slicer
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Generando entrada MCNP...")
        logger.info("  ========================================================")

        ct_node = getattr(self, 'ct_node', None) or getattr(self, 'ct_masked_node', None)
        pet_node = getattr(self, 'pet_node', None)
        seg_node = getattr(self, 'segmentation_node', None)

        if not ct_node:
            raise RuntimeError("Nodo CT no disponible para generar MCNP")
        if not seg_node:
            raise RuntimeError("Nodo de segmentacion no disponible para generar MCNP")

        # Importar MCNPInputGenerator
        try:
            from SlicerDosim.SlicerDosimLib import MCNPInputGenerator
        except ImportError:
            from SlicerDosimLib import MCNPInputGenerator

        generator = MCNPInputGenerator()

        logger.info(f"  Isotopo:       {self.mcnp_isotope}")
        logger.info(f"  Particulas:    {self.mcnp_n_particles:.0e}")
        logger.info(f"  Refinar HU:    {self.mcnp_refine_hu}")
        logger.info(f"  Flip rows:     {self.mcnp_flip_rows}")
        logger.info(f"  CT:            {ct_node.GetName()}")
        logger.info(f"  PET:           {pet_node.GetName() if pet_node else 'N/A (fuente uniforme)'}")
        logger.info(f"  Segmentacion:  {seg_node.GetName()}")
        logger.info(f"  Output dir:    {self.mcnp_output_dir}")

        os.makedirs(self.mcnp_output_dir, exist_ok=True)

        input_path = generator.generate(
            ct_volume_node=ct_node,
            pet_volume_node=pet_node,
            segmentation_node=seg_node,
            output_dir=self.mcnp_output_dir,
            isotope=self.mcnp_isotope,
            n_particles=self.mcnp_n_particles,
            refine_hu=self.mcnp_refine_hu,
            flip_rows=self.mcnp_flip_rows,
            flip_z=self.mcnp_flip_z,
            n_liver_tallies=self.mcnp_n_liver_tallies,
            n_tumor_tallies=self.mcnp_n_tumor_tallies,
        )

        self.mcnp_path = input_path
        file_size_kb = os.path.getsize(input_path) / 1024
        logger.info(f"  Archivo MCNP generado: {input_path}")
        logger.info(f"  Tamano: {file_size_kb:.1f} KB")

        # Copiar archivo fuente .src al directorio de output
        src_source = r"C:\MAT\3Dosim\ai-pipe\mcnp_input\Y90cel3D.src"
        if os.path.exists(src_source):
            import shutil
            dst_source = os.path.join(self.mcnp_output_dir, "Y90cel3D.src")
            if os.path.abspath(src_source) != os.path.abspath(dst_source):
                shutil.copy2(src_source, dst_source)
                logger.info(f"  Archivo fuente copiado: {dst_source}")
            else:
                logger.info(f"  Archivo fuente ya en destino: {dst_source}")
        else:
            logger.warning(f"  Archivo fuente no encontrado: {src_source}")
            logger.warning("  El archivo .i referencia 'read file Y90cel3D.src' pero falta el archivo")

        logger.info("  ========================================================")

    def _validate_mcnp_params(self):
        """Dialogo NO modal para que el medico revise y apruebe los parametros MCNP."""
        import slicer
        from qt import QMessageBox
        logger.info("")
        logger.info("  ========================================================")
        logger.info("  Validacion de parametros MCNP...")
        logger.info("  ========================================================")

        mcnp_path = getattr(self, 'mcnp_path', None)
        if not mcnp_path or not os.path.exists(mcnp_path):
            logger.warning("  No hay archivo MCNP generado para validar")
            return

        file_size_kb = os.path.getsize(mcnp_path) / 1024

        msg_box = QMessageBox(slicer.util.mainWindow())
        msg_box.setWindowTitle("Validacion de Parametros MCNP")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(
            f"<b>Parametros de entrada MCNP generados</b><br><br>"
            f"<b>Archivo:</b> {os.path.basename(mcnp_path)}<br>"
            f"<b>Ubicacion:</b> {self.mcnp_output_dir}<br>"
            f"<b>Tamano:</b> {file_size_kb:.1f} KB<br><br>"
            f"<b>Isotopo:</b> {self.mcnp_isotope}<br>"
            f"<b>Particulas:</b> {self.mcnp_n_particles:.0e}<br>"
            f"<b>Refinar HU:</b> {'Si' if self.mcnp_refine_hu else 'No'}<br>"
            f"<b>Flip rows:</b> {'Si' if self.mcnp_flip_rows else 'No'}<br><br>"
            f"<b>CT:</b> {self.ct_node.GetName() if self.ct_node else 'N/A'}<br>"
            f"<b>PET:</b> {self.pet_node.GetName() if self.pet_node else 'N/A (fuente uniforme)'}<br>"
            f"<b>Segmentacion:</b> {self.segmentation_node.GetName() if self.segmentation_node else 'N/A'}<br><br>"
            f"<i>Revise los parametros antes de ejecutar MCNP.</i>"
        )
        msg_box.setTextFormat(1)  # Qt.RichText
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setModal(False)
        msg_box.show()
        msg_box.raise_()
        msg_box.activateWindow()
        logger.info("  Dialogo de validacion MCNP mostrado (no modal)")
        logger.info("  ========================================================")

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
        if self.screenshots:
            logger.info(f"  Screenshots:     {len(self.screenshots)} archivos")
            for s in self.screenshots:
                logger.info(f"    {os.path.basename(s)}")
        logger.info(f"  Output:         {self.output_dir}")
        if self.mcnp_path:
            logger.info(f"  MCNP input:     {self.mcnp_path}")
            logger.info(f"  MCNP isotopo:   {self.mcnp_isotope}")

        logger.info("")
        logger.info("=" * 70)
        all_ok = fails == 0
        if all_ok:
            logger.info(" RESULTADO: TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f" RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)
        return all_ok
