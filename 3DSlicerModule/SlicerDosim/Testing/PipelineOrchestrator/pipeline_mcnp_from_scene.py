"""
MCNPFromScenePipeline - Pipeline que carga escena .mrb guardada y genera input MCNP.

Flujo:
  1. check_slicer     → Verifica que estamos dentro de 3D Slicer
  2. load_scene       → Carga escena .mrb desde archivo o auto-busca la mas reciente
  3. extract_nodes    → Encuentra CT, PET (opcional) y Segmentacion en la escena
  4. generate_mcnp    → Genera archivo de entrada MCNP via MCNPInputGenerator
  5. validate_mcnp    → Muestra dialogo de validacion de parametros (solo log, no detiene)
  6. report           → Reporte final de resultados

Uso:
    from PipelineOrchestrator.pipeline_mcnp_from_scene import MCNPFromScenePipeline
    p = MCNPFromScenePipeline(scene_path="ruta/escena.mrb", output_dir="C:/salida")
    p.run()
"""

import glob
import logging
import os

from PipelineOrchestrator.pipeline import PipelineTestOrchestrator
from PipelineOrchestrator.views import setup_medical_views, load_pipeline_config
from PipelineOrchestrator.utils import add_module_path

logger = logging.getLogger("3DosimMCNPFromScene")


class MCNPFromScenePipeline(PipelineTestOrchestrator):
    """
    Pipeline que carga una escena .mrb guardada, extrae los nodos
    (CT, PET, segmentacion) y genera el input MCNP.

    Hereda de PipelineTestOrchestrator para reutilizar:
      - Sistema de checkpoints (CheckpointManager)
      - _check_slicer() / _slicer_version()
      - _generate_mcnp_input() con MCNPInputGenerator
      - _validate_mcnp_params() con dialogo Qt
      - _save_scene(), tomar_screenshot()
      - _report(), _save_results_json()
      - Configuracion pipeline_config.jsonc via load_pipeline_config()
    """

    STEP_LOAD_SCENE = "load_scene"
    STEP_EXTRACT_NODES = "extract_nodes"

    def __init__(self, scene_path=None, output_dir=None, config_path="pipeline_config.jsonc",
                 reset=False,
                 mcnp_isotope=None, mcnp_n_particles=None,
                 mcnp_refine_hu=False, mcnp_flip_rows=False, mcnp_flip_z=False,
                 mcnp_n_liver_tallies=None, mcnp_n_tumor_tallies=None):
        """
        Args:
            scene_path: Ruta al archivo .mrb. Si None, busca automaticamente
                        el mas reciente en scene_output_dir del config.
            output_dir: Directorio de salida para MCNP y demas.
                        Si None, usa default del pipeline_config.jsonc.
            config_path: Ruta al pipeline_config.jsonc.
                         Si None, usa el del directorio de PipelineOrchestrator.
            reset: Reiniciar checkpoints (True = empezar de cero).
            mcnp_isotope: Isotopo (Y-90, I-131, Lu-177, Tc-99m).
            mcnp_n_particles: Numero de historias.
            mcnp_refine_hu: Refinar mapeo HU -> materiales.
            mcnp_flip_rows: Invertir eje Y (compatibilidad MATLAB).
            mcnp_flip_z: Invertir eje Z.
            mcnp_n_liver_tallies: Tallies para higado.
            mcnp_n_tumor_tallies: Tallies para tumor.
        """
        # Determinar data_dir para el constructor del padre
        if scene_path and os.path.isfile(scene_path):
            data_dir = os.path.dirname(scene_path)
        elif output_dir:
            data_dir = os.path.dirname(os.path.normpath(output_dir))
        else:
            data_dir = os.getcwd()

        # Inicializar clase padre con valores por defecto
        super().__init__(
            data_dir,
            reset=reset,
            no_consola=True,          # Sin consola interactiva
            segmenter="simple",       # No usado en este pipeline
            stop_before_segment=False,
            force_cpu=True,
            mcnp_isotope=mcnp_isotope,
            mcnp_n_particles=mcnp_n_particles,
            mcnp_refine_hu=mcnp_refine_hu,
            mcnp_flip_rows=mcnp_flip_rows,
            mcnp_flip_z=mcnp_flip_z,
            mcnp_n_liver_tallies=mcnp_n_liver_tallies,
            mcnp_n_tumor_tallies=mcnp_n_tumor_tallies,
        )

        # Sobreescribir output_dir si se proporciona explicitamente
        if output_dir:
            self.output_dir = os.path.abspath(output_dir)
            self.mcnp_output_dir = os.path.join(self.output_dir, "mcnp_input")
            self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")
            # Recrear CheckpointManager con la ruta correcta (el parent lo creo con ruta vieja)
            from PipelineOrchestrator.checkpoint import CheckpointManager
            self.checkpoint = CheckpointManager(self.checkpoint_dir)
            if reset:
                self.checkpoint.reset()
            os.makedirs(self.mcnp_output_dir, exist_ok=True)
            os.makedirs(self.checkpoint_dir, exist_ok=True)

        # Ruta de la escena (.mrb)
        self.scene_path = scene_path
        self.scene_loaded = False

        # Recargar config si se especifica ruta personalizada
        if config_path:
            abs_config_path = config_path
            if not os.path.isabs(config_path):
                abs_config_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    config_path,
                )
            if os.path.exists(abs_config_path):
                self.pipeline_config = load_pipeline_config(abs_config_path)
                # Re-aplicar scene_output_dir desde config
                self.scene_output_dir = self.pipeline_config.get(
                    "scene_output_dir",
                    os.path.join(self.output_dir, "scenes"),
                )

        logger.info("=" * 60)
        logger.info(" MCNPFromScenePipeline")
        logger.info("=" * 60)
        logger.info(f"  Scene path:       {self.scene_path or 'auto-buscar'}")
        logger.info(f"  Output dir:       {self.output_dir}")
        logger.info(f"  Scene output dir: {self.scene_output_dir}")
        logger.info(f"  MCNP output dir:  {self.mcnp_output_dir}")
        logger.info(f"  Isotopo:          {self.mcnp_isotope}")
        logger.info(f"  Particulas:       {self.mcnp_n_particles:.0e}")
        logger.info("")

    # ==================================================================
    # RUN
    # ==================================================================

    def run(self):
        """Ejecuta el pipeline completo desde la escena guardada."""
        logger.info("")
        logger.info("INICIANDO MCNP FROM SCENE PIPELINE")
        logger.info("")

        # --- 1. check_slicer (heredado del padre) ---
        if self._checkpoint_step(
            self.STEP_CHECK_SLICER,
            "Verificando entorno Slicer",
            self._check_slicer,
            data_func=lambda: {"slicer_version": self._slicer_version()},
        ):
            add_module_path()

        # --- 2. load_scene ---
        if not self._checkpoint_step(
            self.STEP_LOAD_SCENE,
            "Cargando escena .mrb",
            self._load_scene,
            data_func=lambda: {
                "scene_path": getattr(self, "scene_path", None),
                "scene_loaded": self.scene_loaded,
            },
        ):
            logger.error("Fallo critico al cargar la escena. Abortando.")
            self._report()
            return
        self._save_scene("01_post_load_scene")
        self.tomar_screenshot("01_load_scene")

        # --- 3. extract_nodes ---
        if not self._checkpoint_step(
            self.STEP_EXTRACT_NODES,
            "Extrayendo nodos de la escena",
            self._extract_nodes,
            data_func=lambda: {
                "ct_node": self.ct_node.GetName() if self.ct_node else None,
                "pet_node": self.pet_node.GetName() if self.pet_node else None,
                "seg_node": self.segmentation_node.GetName() if self.segmentation_node else None,
            },
        ):
            logger.error("No se pudieron extraer los nodos necesarios. Abortando.")
            self._report()
            return

        # Configurar vistas medicas con nodos encontrados
        setup_medical_views(
            ct_node=self.ct_node,
            ct_masked_node=getattr(self, "ct_masked_node", None),
            pet_node=self.pet_node,
            segmentation_node=self.segmentation_node,
            layout_name=self.pipeline_config.get("views", {}).get("layout", "ConventionalView"),
            pet_opacity=self.pipeline_config.get("views", {}).get("pet_opacity", 0.35),
            link_slices=self.pipeline_config.get("views", {}).get("link_slices", True),
        )
        self._save_scene("02_post_extract_nodes")

        # --- 4. generate_mcnp (heredado del padre) ---
        if not self._checkpoint_step(
            self.STEP_GENERATE_MCNP,
            "Generar entrada MCNP ({})".format(self.mcnp_isotope),
            self._generate_mcnp_input,
            data_func=lambda: {
                "mcnp_path": self.mcnp_path,
                "isotope": self.mcnp_isotope,
                "n_particles": self.mcnp_n_particles,
            },
        ):
            logger.error("Generacion de input MCNP fallida. Abortando.")
            self._report()
            return
        self._save_scene("03_mcnp_generated")
        self.tomar_screenshot("03_mcnp_generated")

        # --- 5. validate_mcnp (heredado del padre, solo loggear, no detiene) ---
        self._checkpoint_step(
            self.STEP_VALIDATE_MCNP,
            "Validando parametros MCNP",
            self._validate_mcnp_params,
            data_func=lambda: {"validado": True},
        )
        self._save_scene("04_mcnp_validated")

        # --- 6. report (heredado del padre) ---
        logger.info("")
        logger.info("  PIPELINE MCNP DESDE ESCENA COMPLETADO")
        logger.info("")
        logger.info("  Flujo ejecutado:")
        logger.info("    1. check_slicer     - Verificar 3D Slicer")
        logger.info("    2. load_scene       - Cargar escena .mrb")
        logger.info("    3. extract_nodes    - Extraer CT, PET, Segmentacion")
        logger.info("    4. generate_mcnp    - Generar input MCNP")
        if self.mcnp_path:
            logger.info(f"    5. validate_mcnp   - Validar parametros")
            logger.info("")
            logger.info(f"  Archivo MCNP: {self.mcnp_path}")
        logger.info("")

        ok = self._report()
        if ok:
            logger.info("MCNPFromScenePipeline finalizado EXITOSAMENTE")
        else:
            logger.warning("MCNPFromScenePipeline finalizado con ERRORES. Revise el reporte.")

    # ==================================================================
    # PASOS PERSONALIZADOS
    # ==================================================================

    def _load_scene(self):
        """Carga la escena .mrb usando slicer.util.loadScene().

        Usa self.scene_path si esta definido. Si no, busca automaticamente
        el archivo .mrb mas reciente en scene_output_dir.
        """
        import slicer

        # Determinar ruta de la escena
        scene_path = getattr(self, "scene_path", None)
        if not scene_path or not os.path.exists(scene_path):
            scene_path = self._find_latest_scene()

        if not scene_path or not os.path.exists(scene_path):
            raise FileNotFoundError(
                "No se encontro archivo .mrb. Proporcione --scene valido "
                "o verifique que scene_output_dir contenga escenas guardadas.\n"
                "  Buscado en: {}".format(
                    getattr(self, "scene_output_dir", os.path.join(self.output_dir, "scenes"))
                )
            )

        file_size_mb = os.path.getsize(scene_path) / (1024.0 * 1024.0)
        logger.info(f"  Cargando escena: {scene_path}")
        logger.info(f"  Tamanio: {file_size_mb:.1f} MB")

        try:
            self._log_consola("Cargando escena: {}".format(os.path.basename(scene_path)))
            success = slicer.util.loadScene(scene_path)
            if success:
                self.scene_loaded = True
                logger.info(f"  Escena cargada OK")
                self._log_consola("Escena cargada exitosamente")
            else:
                raise RuntimeError("slicer.util.loadScene() devolvio False")
        except Exception as e:
            raise RuntimeError("Error cargando escena '{}': {}".format(scene_path, e))

    def _find_latest_scene(self) -> "str | None":
        """Busca el archivo .mrb mas reciente en scene_output_dir.

        Returns:
            Ruta al .mrb mas reciente, o None si no hay ninguno.
        """
        scene_dir = getattr(
            self,
            "scene_output_dir",
            os.path.join(self.output_dir, "scenes"),
        )

        if not os.path.isdir(scene_dir):
            logger.warning("  Directorio de escenas no encontrado: {}".format(scene_dir))
            return None

        mrb_files = glob.glob(os.path.join(scene_dir, "*.mrb"))
        if not mrb_files:
            logger.warning("  No hay archivos .mrb en: {}".format(scene_dir))
            return None

        # Ordenar por fecha de modificacion (mas reciente primero)
        mrb_files.sort(key=os.path.getmtime, reverse=True)
        latest = mrb_files[0]
        logger.info("  Ultima escena encontrada: {} ({:.1f} MB)".format(
            latest, os.path.getsize(latest) / (1024.0 * 1024.0),
        ))
        return latest

    def _extract_nodes(self):
        """Busca nodos CT, PET y Segmentacion en la escena cargada.

        Asigna atributos del pipeline:
            self.ct_node           -> vtkMRMLScalarVolumeNode con "CT" en nombre
            self.pet_node          -> vtkMRMLScalarVolumeNode con "PET" en nombre (opcional)
            self.segmentation_node -> vtkMRMLSegmentationNode (preferido)
                                     o vtkMRMLLabelMapVolumeNode (fallback)

        Si no se encuentra CT o segmentacion, lanza RuntimeError.
        PET es opcional (se continua sin el).
        """
        import slicer
        import vtk

        # Obtener todos los nodos de la escena por tipo
        vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        seg_nodes_list = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        labelmap_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")

        logger.info("  Escaneando escena: {} volumenes, {} segmentaciones, {} labelmaps".format(
            len(vol_nodes), len(seg_nodes_list), len(labelmap_nodes),
        ))

        # --- Nodo CT ---
        ct_candidates = [
            n for n in vol_nodes
            if "CT" in n.GetName() or "ct" in n.GetName().lower()
        ]
        if ct_candidates:
            # Preferir CT anonimizado o sin camilla
            preferred = [
                n for n in ct_candidates
                if "anon" in n.GetName().lower() or "sin_camilla" in n.GetName().lower()
            ]
            self.ct_node = preferred[0] if preferred else ct_candidates[0]
            logger.info("  CT encontrado: '{}'".format(self.ct_node.GetName()))
        elif vol_nodes:
            # Fallback: tomar el primer volumen escalar disponible
            self.ct_node = vol_nodes[0]
            logger.info("  CT (fallback - primer volumen): '{}'".format(self.ct_node.GetName()))
        else:
            raise RuntimeError("No se encontraron volumenes escalares en la escena")

        # --- Nodo PET (opcional) ---
        pet_candidates = [
            n for n in vol_nodes
            if "PET" in n.GetName() or "pet" in n.GetName().lower()
        ]
        if pet_candidates:
            self.pet_node = pet_candidates[0]
            logger.info("  PET encontrado: '{}'".format(self.pet_node.GetName()))
        else:
            self.pet_node = None
            logger.info("  PET no encontrado (se usara fuente uniforme en MCNP)")

        # --- Nodo de Segmentacion ---
        seg_found = None
        if seg_nodes_list:
            # Preferir segmentacion con TotalSegmentator o simplemente la primera
            ts_candidates = [
                n for n in seg_nodes_list
                if "TotalSegmentator" in n.GetName() or "Segmentation" in n.GetName()
            ]
            seg_found = ts_candidates[0] if ts_candidates else seg_nodes_list[0]
            logger.info("  Segmentacion (vtkMRMLSegmentationNode): '{}'".format(seg_found.GetName()))

            # Contar segmentos
            seg_ids = vtk.vtkStringArray()
            seg_found.GetSegmentation().GetSegmentIDs(seg_ids)
            logger.info("    Segmentos: {}".format(seg_ids.GetNumberOfValues()))
        elif labelmap_nodes:
            # Fallback: usar labelmap volume como segmentacion
            seg_found = labelmap_nodes[0]
            logger.info("  Segmentacion (vtkMRMLLabelMapVolumeNode - fallback): '{}'".format(
                seg_found.GetName(),
            ))
        else:
            raise RuntimeError(
                "No se encontraron nodos de segmentacion en la escena. "
                "Se requiere vtkMRMLSegmentationNode o vtkMRMLLabelMapVolumeNode."
            )

        self.segmentation_node = seg_found

        # Detectar si hay nodo CT sin camilla (para visualizacion)
        masked_candidates = [
            n for n in vol_nodes
            if "sin_camilla" in n.GetName().lower() or "masked" in n.GetName().lower()
        ]
        if masked_candidates:
            self.ct_masked_node = masked_candidates[0]
            logger.info("  CT_masked encontrado: '{}'".format(self.ct_masked_node.GetName()))

        logger.info("  Nodos extraidos correctamente")
