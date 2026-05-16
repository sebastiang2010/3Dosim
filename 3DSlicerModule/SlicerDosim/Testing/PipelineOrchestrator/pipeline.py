"""
PipelineTestOrchestrator - Orquesta el pipeline completo 3Dosim en Slicer.

Pasos:
  1. Verificar entorno Slicer
  2. Cargar DICOM (CT + PET)
  3. Anonimizar
  4. Eliminar camilla y aire del CT
  5. Segmentar con TotalSegmentator (+ barra de progreso)
  6. Validacion medica obligatoria
  7. Exportar NIfTI
  8. Generar entrada MCNP
  9. Reporte final + commit git
"""

import logging
import os
import time

from .checkpoint import CheckpointManager
from . import anonymize
from . import couch_remover
from . import segmentation
from . import validation
from . import mcnp_builder
from . import git_commit
from .utils import logger, add_module_path, show_progress

logger = logging.getLogger("3DosimTest")


class PipelineTestOrchestrator:
    """
    Orquesta y verifica el pipeline completo 3Dosim en 3D Slicer.
    Todos los pasos tienen checkpoint: si se corta, retoma desde donde quedo.
    """

    # Nombres internos de cada paso (para checkpoints)
    STEP_CHECK_SLICER  = "check_slicer"
    STEP_LOAD_DICOM    = "load_dicom"
    STEP_ANONYMIZE     = "anonymize"
    STEP_REMOVE_COUCH  = "remove_couch_air"
    STEP_SEGMENT       = "segment_phantom"
    STEP_VALIDATE      = "validate_segmentation"
    STEP_EXPORT_NIFTI  = "export_nifti"
    STEP_GENERATE_MCNP = "generate_mcnp"

    def __init__(self, data_dir: str, reset: bool = False):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")
        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")
        self.anon_dir = os.path.join(self.output_dir, ".anon")

        self.results = {
            "pasos": [],
            "errores": [],
            "tiempos": {},
        }

        # Checkpoint manager
        self.checkpoint = CheckpointManager(self.checkpoint_dir)
        if reset:
            self.checkpoint.reset()

        # Nodos Slicer (se llenan durante el pipeline)
        self.ct_node = None
        self.pet_node = None
        self.segmentation_node = None
        self.phantom_nifti_path = None
        self.mcnp_path = None

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Orchestrator v3.14")
        logger.info("=" * 60)
        logger.info(f"Datos:        {self.data_dir}")
        logger.info(f"Output:       {self.output_dir}")
        logger.info(f"Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info("")

    # ==================================================================
    # RUN
    # ==================================================================

    def run(self):
        """Ejecuta el pipeline completo con checkpoints."""
        logger.info("")
        logger.info("INICIANDO PIPELINE")
        logger.info("")

        # Paso 1: Verificar Slicer + paths
        if self._checkpoint_step(self.STEP_CHECK_SLICER, "Verificando entorno Slicer",
                                 self._check_slicer):
            add_module_path()

        # Paso 2: Cargar DICOM
        self._checkpoint_step(self.STEP_LOAD_DICOM, "Cargando imagenes DICOM",
                              self._load_dicom)

        # Paso 3: Anonimizar
        self._checkpoint_step(self.STEP_ANONYMIZE, "Anonimizando imagenes",
                              self._anonymize)

        # Paso 4: Quitar camilla y aire
        self._checkpoint_step(self.STEP_REMOVE_COUCH, "Eliminando camilla y aire",
                              self._remove_couch_air)

        # Paso 5: Segmentar con TotalSegmentator (+ progreso)
        self._checkpoint_step(self.STEP_SEGMENT, "Segmentando (TotalSegmentator)",
                              self._segment)

        # Paso 6: Validacion medica obligatoria
        self._checkpoint_step(self.STEP_VALIDATE, "Validacion medica de la segmentacion",
                              self._do_validation)

        # Paso 7: Exportar NIfTI
        self._checkpoint_step(self.STEP_EXPORT_NIFTI, "Exportando phantom a NIfTI",
                              self._export_nifti)

        # Paso 8: Generar entrada MCNP
        self._checkpoint_step(self.STEP_GENERATE_MCNP, "Generando entrada MCNP (Modulo 2)",
                              self._generate_mcnp)

        # Reporte final
        ok = self._report()

        # Si todo OK -> preguntar por commit
        if ok:
            git_commit.prompt_git_commit(self.data_dir)

    # ==================================================================
    # CHECKPOINT STEP
    # ==================================================================

    def _checkpoint_step(self, step_name: str, display_name: str, func):
        """
        Ejecuta un paso solo si no esta en checkpoint.
        Si ya fue completado, lo salta.
        """
        # Verificar checkpoint
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [{'...'}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
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
            self.checkpoint.mark_completed(step_name)
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

    # ==================================================================
    # PASOS DEL PIPELINE
    # ==================================================================

    def _check_slicer(self):
        """Verifica que estamos dentro de 3D Slicer."""
        try:
            import slicer
            logger.info(f"  Slicer version: {slicer.app.majorVersion}.{slicer.app.minorVersion}")
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    def _load_dicom(self):
        """Carga DICOM usando DICOMUtils con DB temporal."""
        import slicer
        from DICOMLib import DICOMUtils

        for d in [self.ct_dir, self.pet_dir]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio no encontrado: {d}")

        ct_files = [f for f in os.listdir(self.ct_dir) if f.endswith('.dcm') or f.isdigit()]
        pet_files = [f for f in os.listdir(self.pet_dir) if f.endswith('.dcm') or f.isdigit()]
        logger.info(f"  Archivos CT: {len(ct_files)}")
        logger.info(f"  Archivos PET: {len(pet_files)}")

        # DB temporal
        original_db_dir = DICOMUtils.openTemporaryDatabase()
        logger.info("  DB temporal abierta")

        try:
            for dir_path, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
                logger.info(f"  Indexando {label}...")
                ok = DICOMUtils.importDicom(dir_path)
                if not ok:
                    raise RuntimeError(f"Fallo indexacion {label}")
                logger.info(f"  {label} indexado")

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
        logger.info("  DB original restaurada")

        # Identificar CT y PET
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

        # Fallback por orden
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

    def _anonymize(self):
        """Paso de anonimizacion."""
        anonymize.anonymize(
            self.ct_node, self.ct_dir, self.pet_dir,
            self.anon_dir, self.pet_node
        )

    def _remove_couch_air(self):
        """Paso de eliminacion de camilla y aire."""
        couch_remover.remove_couch_and_air(self.ct_node)

    def _segment(self):
        """Paso de segmentacion."""
        seg_node = segmentation.run_segmentation(self.ct_node, self.output_dir)
        self.segmentation_node = seg_node

    def _do_validation(self):
        """Paso de validacion medica."""
        validation.validate_segmentation()

    def _export_nifti(self):
        """Exporta phantom a NIfTI."""
        logger.info("  Export NIfTI: saltado (no necesario para Mod 2)")
        self.phantom_nifti_path = None

    def _generate_mcnp(self):
        """Paso de generacion de entrada MCNP."""
        mcnp_path = mcnp_builder.generate_mcnp_input(
            self.ct_node, self.output_dir, self.data_dir
        )
        self.mcnp_path = mcnp_path

    # ==================================================================
    # REPORTE
    # ==================================================================

    def _report(self) -> bool:
        """Genera reporte final. Returns: True si todos los pasos fueron exitosos."""
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
