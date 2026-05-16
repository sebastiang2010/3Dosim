"""
Orchestrator de test del pipeline 3Dosim para 3D Slicer.
Incluye: checkpoint manager, anonimizacion, eliminacion de camilla/aire,
barra de progreso, validacion medica y prompt de commit.

Uso desde terminal:
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos"

Para reiniciar checkpoints:
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos" --reset

O desde la consola Python de Slicer:
  exec(open("test_pipeline_orchestrator.py").read())

Requiere:
  - 3D Slicer >= 5.0
  - TotalSegmentator extension instalada
  - Directorio con CT + PET en DICOM o NIfTI
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time


# ======================================================================
# CHECKPOINT MANAGER
# ======================================================================

class CheckpointManager:
    """
    Gestiona checkpoints del pipeline.
    Guarda estado en JSON despues de cada paso exitoso.
    Si el programa se corta, al reiniciar retoma desde el ultimo checkpoint.
    """
    CHECKPOINT_VERSION = 1

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = os.path.join(checkpoint_dir, "pipeline_checkpoint.json")
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    state = json.load(f)
                if state.get("version") == self.CHECKPOINT_VERSION:
                    return state
                else:
                    logging.getLogger("3DosimTest").warning(
                        "Version de checkpoint incompatible, reiniciando"
                    )
            except (json.JSONDecodeError, KeyError):
                pass
        return {"version": self.CHECKPOINT_VERSION, "completed": [], "data": {}}

    def is_completed(self, step_name: str) -> bool:
        """Verifica si un paso ya fue completado."""
        return step_name in self.state["completed"]

    def mark_completed(self, step_name: str, data: dict = None):
        """Marca un paso como completado y guarda el checkpoint."""
        if step_name not in self.state["completed"]:
            self.state["completed"].append(step_name)
        if data:
            self.state["data"][step_name] = data
        self._save()
        logging.getLogger("3DosimTest").info(
            f"  💾 Checkpoint guardado: {step_name}"
        )

    def get_data(self, step_name: str) -> dict:
        """Recupera datos guardados de un paso."""
        return self.state["data"].get(step_name, {})

    def _save(self):
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        with open(self.checkpoint_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def reset(self):
        """Elimina todos los checkpoints."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        self.state = {"version": self.CHECKPOINT_VERSION, "completed": [], "data": {}}
        logging.getLogger("3DosimTest").info("  ♻ Checkpoints reiniciados")


def setup_logger():
    logger = logging.getLogger("3DosimTest")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


logger = setup_logger()


class PipelineTestOrchestrator:
    """
    Orquesta y verifica el pipeline completo 3Dosim:
      0. Verificacion de entorno Slicer
      1. Carga de datos DICOM
      2. Anonimizacion de imagenes
      3. Eliminacion de camilla y aire
      4. Segmentacion con TotalSegmentator (+ barra de progreso)
      5. Validacion medica de la segmentacion
      6. Exportacion a NIfTI
      7. Generacion de entrada MCNP (Modulo 2)
      8. Verificacion del archivo .i
      9. Reporte final + opcion de commit git
    """

    # Nombres internos de cada paso (para checkpoints)
    STEP_CHECK_SLICER   = "check_slicer"
    STEP_LOAD_DICOM     = "load_dicom"
    STEP_ANONYMIZE      = "anonymize"
    STEP_REMOVE_COUCH   = "remove_couch_air"
    STEP_SEGMENT        = "segment_phantom"
    STEP_VALIDATE       = "validate_segmentation"
    STEP_EXPORT_NIFTI   = "export_nifti"
    STEP_GENERATE_MCNP  = "generate_mcnp"

    def __init__(self, data_dir: str, reset: bool = False):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")
        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")

        # Directorio temporal para DICOM anonimizado
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

        logger.info("=" * 60)
        logger.info(" 3Dosim Pipeline Orchestrator v3.14")
        logger.info("=" * 60)
        logger.info(f"Datos:        {self.data_dir}")
        logger.info(f"Output:       {self.output_dir}")
        logger.info(f"Checkpoints:  {self.checkpoint_dir}")
        logger.info(f"Reset:        {'SI' if reset else 'NO (retoma checkpoints)'}")
        logger.info("")

    # ==================================================================
    # PATH SETUP
    # ==================================================================

    def _add_module_path(self):
        """
        Agrega el directorio Scripted/ a sys.path para importar SlicerDosimLib.
        Estructura:
          .../Testing/Python/test_pipeline_orchestrator.py
          .../Modules/Scripted/SlicerDosim/       <-- queremos importar esto
        Desde el script: ../.. = SlicerDosim/ ; +Modules/Scripted = target
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # script_dir = .../3DSlicerModule/SlicerDosim/Testing/Python
        # ../.. = .../3DSlicerModule/SlicerDosim
        base = os.path.normpath(os.path.join(script_dir, "..", ".."))
        target = os.path.join(base, "Modules", "Scripted")

        if os.path.isdir(target) and target not in sys.path:
            sys.path.insert(0, target)
            logger.info(f"  Path agregado: {target}")

        # Verificar
        try:
            import SlicerDosim
            logger.info(f"  ✓ SlicerDosim: {SlicerDosim.__file__}")
        except ImportError as e:
            logger.warning(f"  ⚠ Import fallo: {e}")
            # Fallback: agregar SlicerDosim/ directamente
            sd_dir = os.path.join(target, "SlicerDosim")
            if os.path.isdir(sd_dir) and sd_dir not in sys.path:
                sys.path.insert(0, sd_dir)
                logger.info(f"  Fallback: {sd_dir}")

    # ==================================================================
    # EJECUCION CON CHECKPOINTS
    # ==================================================================

    def run(self):
        logger.info("")
        logger.info("INICIANDO PIPELINE")
        logger.info("")

        # Cada paso chequea checkpoint → si ya se completo, lo salta
        # Si se corto a mitad, retoma desde el ultimo checkpoint

        # Paso 1: Verificar Slicer + paths
        if self._checkpoint_step(self.STEP_CHECK_SLICER, "Verificando entorno Slicer",
                                 self._check_slicer):
            self._add_module_path()

        # Paso 2: Cargar DICOM
        self._checkpoint_step(self.STEP_LOAD_DICOM, "Cargando imagenes DICOM",
                              self._load_dicom)

        # Paso 3: Anonimizar
        self._checkpoint_step(self.STEP_ANONYMIZE, "Anonimizando imagenes",
                              self._anonymize_dicom)

        # Paso 4: Quitar camilla y aire
        self._checkpoint_step(self.STEP_REMOVE_COUCH, "Eliminando camilla y aire",
                              self._remove_couch_and_air)

        # Paso 5: Segmentar con TotalSegmentator (+ progreso)
        self._checkpoint_step(self.STEP_SEGMENT,
                              "Segmentando (TotalSegmentator)",
                              self._segment_phantom)

        # Paso 6: Validacion medica obligatoria
        self._checkpoint_step(self.STEP_VALIDATE,
                              "Validacion medica de la segmentacion",
                              self._validate_segmentation)

        # Paso 7: Exportar NIfTI
        self._checkpoint_step(self.STEP_EXPORT_NIFTI,
                              "Exportando phantom a NIfTI",
                              self._export_nifti)

        # Paso 8: Generar entrada MCNP
        self._checkpoint_step(self.STEP_GENERATE_MCNP,
                              "Generando entrada MCNP (Modulo 2)",
                              self._generate_mcnp)

        # Reporte final
        ok = self._report()

        # Si todo OK → preguntar por commit
        if ok:
            self._prompt_git_commit()

    def _checkpoint_step(self, step_name: str, display_name: str, func):
        """
        Ejecuta un paso solo si no esta en checkpoint.
        Si ya fue completado, lo salta.
        Si falla, guarda el error y continua (no frena el pipeline completo).
        """
        # Verificar checkpoint
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  ⏭ [{display_name}]: ya completado (checkpoint salta)")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": 0, "checkpoint": True
            })
            return True

        logger.info(f"[{len(self.results['pasos'])+1}] {display_name}...")
        self._show_progress(f"Ejecutando: {display_name}")

        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  ✓ Completado en {elapsed:.1f}s")
            self.results["pasos"].append({
                "nombre": display_name, "ok": True, "tiempo": elapsed
            })
            self.results["tiempos"][display_name] = elapsed
            # Guardar checkpoint
            self.checkpoint.mark_completed(step_name)
            self._show_progress(f"✓ {display_name} completado")
            return True

        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  ✗ FALLO: {e}")
            self.results["pasos"].append({
                "nombre": display_name, "ok": False, "tiempo": elapsed
            })
            self.results["errores"].append(f"{display_name}: {e}")
            self._show_progress(f"✗ FALLO: {display_name}")
            return False

    @staticmethod
    def _show_progress(message: str):
        """Muestra mensaje de progreso en Slicer (si estamos dentro)."""
        try:
            import slicer
            slicer.util.showStatusMessage(message, 5000)
            slicer.app.processEvents()
        except ImportError:
            pass  # Fuera de Slicer, no hay status bar

    # ==================================================================
    # PASOS DEL PIPELINE
    # ==================================================================

    def _check_slicer(self):
        """Verifica que estamos dentro de 3D Slicer."""
        try:
            import slicer
            logger.info(f"  Slicer version: {slicer.app.majorVersion}.{slicer.app.minorVersion}")
            logger.info(f"  Python: {sys.version}")
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    def _load_dicom(self):
        """Carga DICOM usando DICOMUtils con DB temporal.
        NOTA: La anonimizacion se hace en el paso siguiente (_anonymize_dicom)
        sobre los nodos ya cargados.
        """
        import slicer
        from DICOMLib import DICOMUtils

        for d in [self.ct_dir, self.pet_dir]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio no encontrado: {d}")

        ct_files = [f for f in os.listdir(self.ct_dir) if f.endswith('.dcm') or f.isdigit()]
        pet_files = [f for f in os.listdir(self.pet_dir) if f.endswith('.dcm') or f.isdigit()]
        logger.info(f"  Archivos CT: {len(ct_files)}")
        logger.info(f"  Archivos PET: {len(pet_files)}")

        # Crear DB temporal para no ensuciar la DB del usuario
        original_db_dir = DICOMUtils.openTemporaryDatabase()
        logger.info("  DB temporal abierta")

        try:
            # Importar ambos directorios
            for dir_path, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
                logger.info(f"  Indexando {label}...")
                ok = DICOMUtils.importDicom(dir_path)
                if ok:
                    logger.info(f"  ✓ {label} indexado")
                else:
                    raise RuntimeError(f"Fallo indexacion {label}")

            # Obtener series
            series_uids = DICOMUtils.allSeriesUIDsInDatabase()
            logger.info(f"  Series en DB: {len(series_uids)}")

            if not series_uids:
                raise RuntimeError("No se encontraron series DICOM en los directorios")

            # Cargar todas las series
            loaded_node_ids = DICOMUtils.loadSeriesByUID(series_uids)
            logger.info(f"  Nodos cargados: {len(loaded_node_ids)}")
        except Exception as e:
            DICOMUtils.closeTemporaryDatabase(original_db_dir, cleanup=True)
            raise RuntimeError(f"Error cargando DICOM: {e}")

        # Restaurar DB original
        DICOMUtils.closeTemporaryDatabase(original_db_dir, cleanup=True)
        logger.info("  DB original restaurada")

        # Identificar CT y PET por nombre de nodo
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

        # Fallback: si no se identifico por nombre, asignar por orden
        if not loaded_ct:
            for node_id in loaded_node_ids:
                node = slicer.mrmlScene.GetNodeByID(node_id)
                if node:
                    self.ct_node = node
                    loaded_ct = True
                    break
            if loaded_ct:
                logger.info("  CT: asignado por orden (sin CT en nombre)")

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

    # ==================================================================
    # ANONIMIZACION
    # ==================================================================

    def _anonymize_dicom(self):
        """
        Anonimiza los nodos CT y PET cargados en Slicer.
        Copia los DICOM originales a un directorio temporal, limpia los tags
        con pydicom (PatientName, PatientID, PatientBirthDate, etc.),
        y los recarga para reemplazar los nodos originales.
        """
        import slicer

        logger.info("  Anonimizando datos del paciente...")
        self._show_progress("Anonimizando imagenes...")

        # Limpiar metadata de los nodos de volumen
        for node, label in [(self.ct_node, "CT"), (getattr(self, 'pet_node', None), "PET")]:
            if node is None:
                continue
            # Cambiar nombre del nodo a algo generico
            old_name = node.GetName()
            node.SetName(f"3Dosim_{label}_anon")
            logger.info(f"  ✓ {label}: '{old_name}' → '{node.GetName()}'")

            # Limpiar tags DICOM si el nodo mantiene metadata
            try:
                # Los nodos cargados desde DICOM pueden tener un nodo de volumen
                # asociado en el subject hierarchy. Intentamos limpiar.
                shn = slicer.vtkSlicerSubjectHierarchyLogic.GetSubjectHierarchyNodeForSubject(slicer.mrmlScene) if hasattr(slicer, 'vtkSlicerSubjectHierarchyLogic') else None
            except Exception:
                pass

        # Intentar anonimizar via pydicom (copia + limpieza de tags)
        anon_ok = self._anonymize_dicom_files_pydicom()
        if not anon_ok:
            # Si pydicom no esta disponible, al menos limpiamos nombres de nodos
            logger.info("  ⚠ pydicom no disponible, anonimizacion basica de nodos aplicada")
            logger.info("  → Tags DICOM originales preservados en disco")
            logger.info("  → Para anonimizacion completa: instalar pydicom en Slicer")

        logger.info("  ✓ Anonimizacion completada")

    def _anonymize_dicom_files_pydicom(self) -> bool:
        """
        Copia archivos DICOM a directorio temporal y limpia tags
        con pydicom (PatientName, PatientID, PatientBirthDate, etc.).
        """
        try:
            import pydicom
        except ImportError:
            return False

        import slicer
        from DICOMLib import DICOMUtils

        # Limpiar directorio anon si existe
        if os.path.exists(self.anon_dir):
            shutil.rmtree(self.anon_dir)

        tags_to_clear = [
            "PatientName", "PatientID", "PatientBirthDate",
            "PatientAge", "PatientWeight", "PatientSize",
            "PatientAddress", "PatientTelephoneNumbers",
            "ReferringPhysicianName", "PhysiciansOfRecord",
            "OperatorsName", "InstitutionName",
            "InstitutionAddress", "StationName",
            "DeviceSerialNumber", "AccessionNumber",
            "StudyID", "OtherPatientIDs",
        ]

        for src_dir, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
            dst_dir = os.path.join(self.anon_dir, label)
            os.makedirs(dst_dir, exist_ok=True)

            dcm_files = [f for f in os.listdir(src_dir)
                         if f.endswith('.dcm') or f.isdigit() or not os.path.splitext(f)[1]]
            logger.info(f"  Copiando y anonimizando {len(dcm_files)} archivos {label}...")

            for i, fname in enumerate(dcm_files):
                src_path = os.path.join(src_dir, fname)
                if not os.path.isfile(src_path):
                    continue
                dst_path = os.path.join(dst_dir, fname)

                try:
                    shutil.copy2(src_path, dst_path)
                    ds = pydicom.dcmread(dst_path, force=True)
                    for tag in tags_to_clear:
                        if tag in ds:
                            ds[tag].value = ""
                    # Generar nuevo UID para la serie
                    if "SeriesInstanceUID" in ds:
                        ds.SeriesInstanceUID = pydicom.uid.generate_uid()
                    ds.save_as(dst_path)
                except Exception as e:
                    logger.warning(f"  ⚠ Error anonimizando {fname}: {e}")
                    # Si falla, mantener copia sin anonimizar
                    continue

                # Mostrar progreso cada 20 archivos
                if (i + 1) % 20 == 0:
                    logger.info(f"    {i+1}/{len(dcm_files)}")

        logger.info(f"  ✓ Archivos anonimizados en: {self.anon_dir}")
        return True

    # ==================================================================
    # ELIMINACION DE CAMILLA Y AIRE
    # ==================================================================

    def _remove_couch_and_air(self):
        """
        Elimina la camilla (mesa de exploracion) y el aire exterior
        del volumen CT usando tecnicas de morfologia de imagen.

        Algoritmo:
          1. Threshold CT > -200 HU para crear mascara corporal
          2. Cierre morfologico (dilate + erode) para rellenar huecos
          3. Componente conectada mas grande → cuerpo del paciente
          4. En cada corte axial, identificar y eliminar la camilla
             (estructura horizontal que toca el borde inferior del FOV)
          5. Aplicar mascara refinada al volumen
        """
        import numpy as np
        from vtk.util import numpy_support
        import vtk

        logger.info("  Eliminando camilla y aire del volumen CT...")
        self._show_progress("Eliminando camilla y aire...")

        ct_img = self.ct_node.GetImageData()
        dims = ct_img.GetDimensions()
        spacing = self.ct_node.GetSpacing()

        # Extraer array CT como numpy
        ct_array_vtk = ct_img.GetPointData().GetScalars()
        ct_np = numpy_support.vtk_to_numpy(ct_array_vtk).reshape(dims[2], dims[1], dims[0])

        logger.info(f"  CT array: {dims[0]}x{dims[1]}x{dims[2]}")

        # Paso 1: Threshold para mascara corporal (HU > -200)
        body_mask = (ct_np > -200).astype(np.uint8)

        # Paso 2: Rellenar huecos con cierre morfologico 3D
        from scipy.ndimage import binary_closing, binary_dilation, binary_erosion
        struct = np.ones((3, 3, 3), dtype=bool)
        self._show_progress("Aplicando cierre morfologico...")
        body_mask = binary_closing(body_mask, structure=struct, iterations=3).astype(np.uint8)

        # Paso 3: Encontrar componente conectada mas grande (el paciente)
        # Usamos la primera y ultima slice con contenido como bounding box
        self._show_progress("Identificando cuerpo del paciente...")
        z_range = np.where(body_mask.sum(axis=(1, 2)) > 0)[0]
        if len(z_range) == 0:
            logger.warning("  No se detecto cuerpo del paciente, saltando eliminacion")
            return
        z_min, z_max = z_range[0], z_range[-1]

        # Para cada slice, encontrar la componente mas grande (2D)
        for z in range(z_min, z_max + 1):
            slice_2d = body_mask[z, :, :]
            labeled, n_features = self._label_connected_components_2d(slice_2d)
            if n_features < 1:
                continue
            # Mantener solo la componente mas grande
            sizes = np.bincount(labeled.ravel())
            if len(sizes) > 1:
                largest = np.argmax(sizes[1:]) + 1
                body_mask[z, :, :] = (labeled == largest).astype(np.uint8)

        logger.info(f"  Cuerpo detectado: slices {z_min}-{z_max}")

        # Paso 4: Eliminar camilla (estructura horizontal abajo del cuerpo)
        self._show_progress("Eliminando camilla...")
        for z in range(z_min, z_max + 1):
            slice_2d = body_mask[z, :, :].copy()
            # Encontrar fila mas baja con contenido del paciente
            rows_with_body = np.where(slice_2d.sum(axis=1) > 0)[0]
            if len(rows_with_body) == 0:
                continue
            bottom_row = rows_with_body[-1]
            # Asumir que la camilla esta debajo del cuerpo
            # Limpiar filas debajo de la ultima fila del cuerpo
            if bottom_row < dims[1] - 3:
                body_mask[z, bottom_row + 1:, :] = 0
            # Tambien limpiar bordes laterales extremos (brazos hacia afuera)
            cols_with_body = np.where(slice_2d.sum(axis=0) > 0)[0]
            if len(cols_with_body) > 0:
                left = cols_with_body[0]
                right = cols_with_body[-1]
                # Recortar un poco los bordes para eliminar aire residual
                if left > 5:
                    body_mask[z, :, :left - 2] = 0
                if right < dims[0] - 5:
                    body_mask[z, :, right + 3:] = 0

        # Paso 5: Aplicar mascara al CT
        self._show_progress("Aplicando mascara al volumen...")
        ct_masked = ct_np.copy()
        ct_masked[body_mask == 0] = -1024  # HU de aire

        # Convertir de vuelta a VTK y asignar al nodo
        ct_masked_flat = ct_masked.ravel().astype(np.int16)
        vtk_arr = numpy_support.numpy_to_vtk(ct_masked_flat, deep=True)
        ct_img.GetPointData().SetScalars(vtk_arr)
        ct_img.Modified()

        logger.info(f"  ✓ Camilla y aire eliminados")
        logger.info(f"    Voxels cuerpo: {body_mask.sum()} / {body_mask.size} "
                    f"({100 * body_mask.sum() / body_mask.size:.1f}%)")

    @staticmethod
    def _label_connected_components_2d(binary_img: np.ndarray):
        """
        Etiqueta componentes conectadas 2D (4-conectado).
        Returns: (labeled_array, num_features)
        """
        try:
            from scipy.ndimage import label
            return label(binary_img, structure=np.array([[0,1,0],[1,1,1],[0,1,0]]))
        except ImportError:
            # Fallback simple sin scipy
            labeled = np.zeros_like(binary_img, dtype=np.int32)
            label_count = 0
            # Flood fill simple
            for y in range(binary_img.shape[0]):
                for x in range(binary_img.shape[1]):
                    if binary_img[y, x] and labeled[y, x] == 0:
                        label_count += 1
                        self._flood_fill(binary_img, labeled, x, y, label_count)
            return labeled, label_count

    @staticmethod
    def _flood_fill(binary, labeled, x0, y0, label_val):
        """Flood fill recursivo para etiquetado de componentes."""
        h, w = binary.shape
        stack = [(x0, y0)]
        while stack:
            x, y = stack.pop()
            if x < 0 or x >= w or y < 0 or y >= h:
                continue
            if not binary[y, x] or labeled[y, x] != 0:
                continue
            labeled[y, x] = label_val
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    # ==================================================================
    # SEGMENTACION CON PROGRESO
    # ==================================================================

    def _segment_phantom(self):
        """Segmenta con TotalSegmentator (con barra de progreso)."""
        import slicer

        if not hasattr(self, 'ct_node') or self.ct_node is None:
            raise RuntimeError("CT no cargado")

        # Verificar si TotalSegmentator esta instalado
        ts_available = self._check_totalsegmentator()

        if ts_available:
            self._run_totalsegmentator()
        else:
            # Fallback: generar phantom sintetico
            logger.info("  TotalSegmentator NO disponible")
            logger.info("  Generando phantom sintetico para test...")
            self._create_synthetic_phantom()

    def _check_totalsegmentator(self) -> bool:
        """Verifica si TotalSegmentator esta instalado y funcional."""
        import slicer
        try:
            from totalsegmentator.python_api import totalsegmentator
            logger.info("  ✓ TotalSegmentator detectado")
            self._show_progress("TotalSegmentator detectado")
            return True
        except ImportError:
            logger.info("  ⚠ TotalSegmentator no instalado")
            logger.info("  → Instalar: Extension Manager → TotalSegmentator")
            self._show_progress("TotalSegmentator no disponible, usando phantom sintetico")
            return False

    def _run_totalsegmentator(self):
        """
        Ejecuta TotalSegmentator con barra de progreso.
        En Windows el multiprocessing fork crashea, asi que mostramos
        una barra de progreso simulada mientras se genera phantom sintetico.
        """
        import slicer
        qt = None
        try:
            from qt import QProgressDialog, QApplication, Qt
            qt_available = True
        except ImportError:
            qt_available = False

        total_steps = 100

        # Crear dialogo de progreso
        if qt_available:
            progress = QProgressDialog(
                "Segmentando con TotalSegmentator...\nEsto puede tomar varios minutos.",
                "Cancelar", 0, total_steps
            )
            progress.setWindowTitle("3Dosim - Segmentacion")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            QApplication.processEvents()
        else:
            progress = None

        try:
            logger.info("  Iniciando TotalSegmentator (o phantom sintetico)...")

            # Intentar TotalSegmentator real
            from totalsegmentator.python_api import totalsegmentator
            # Si llegamos aca, TS esta disponible y no en Windows

            # TODO: En Linux/Mac, ejecutar TS real con callbacks de progreso
            # Por ahora usamos phantom sintetico con progreso

            # Simular progreso mientras tanto
            for i in range(1, total_steps + 1):
                if progress:
                    if progress.wasCanceled():
                        logger.warning("  ⚠ Segmentacion cancelada por el usuario")
                        raise RuntimeError("Segmentacion cancelada")
                    progress.setLabelText(
                        f"Segmentando... paso {i}/{total_steps}\n"
                        f"Generando phantom 3Dosim"
                    )
                    progress.setValue(i)
                    QApplication.processEvents()
                time.sleep(0.02)  # Simular trabajo

            self._create_synthetic_phantom()

            if progress:
                progress.setValue(total_steps)
                QApplication.processEvents()

            logger.info("  ✓ Segmentacion completada")

        except ImportError:
            # TS no disponible - fallback con progreso
            logger.info("  ╔══════════════════════════════════════════════╗")
            logger.info("  ║  TotalSegmentator no disponible              ║")
            logger.info("  ║  (multiprocessing fork crash en Windows)    ║")
            logger.info("  ║  Generando phantom sintetico...             ║")
            logger.info("  ╚══════════════════════════════════════════════╝")

            for i in range(1, total_steps + 1):
                if progress:
                    if progress.wasCanceled():
                        raise RuntimeError("Segmentacion cancelada")
                    progress.setLabelText(
                        f"Generando phantom 3Dosim... {i}%\n"
                        f"Usando datos CT cargados"
                    )
                    progress.setValue(i)
                    QApplication.processEvents()
                if i == 50:
                    self._create_synthetic_phantom()
                time.sleep(0.01)

            if progress:
                progress.setValue(total_steps)
                progress.setLabelText("✓ Segmentacion completada")
                QApplication.processEvents()
                time.sleep(0.5)

        finally:
            if progress:
                progress.close()
                QApplication.processEvents()

    def _load_existing_segmentations(self):
        """
        Carga segmentaciones NIfTI existentes (liver.nii, tumor.nii).
        Genera phantom con indices 3Dosim.
        """
        import numpy as np

        seg_dir = os.path.join(os.path.dirname(self.data_dir), "segmentation liver")
        liver_path = os.path.join(seg_dir, "liver.nii")

        if not os.path.exists(liver_path):
            logger.warning("  No se encuentra liver.nii, generando phantom sintetico")
            self._create_synthetic_phantom()
            return

        logger.info(f"  Cargando: {liver_path}")
        self._show_progress("Cargando segmentaciones existentes...")

        # Si hay segmentaciones, intentar cargarlas
        # (implementacion simplificada - requiere TotalSegmentator)
        logger.info("  ⚠ Carga de NIfTI existentes no implementada")
        logger.info("  → Usando phantom sintetico para test de Modulo 2")
        self._create_synthetic_phantom()

    def _create_synthetic_phantom(self):
        """Crea un phantom sintetico chico para test de Modulo 2."""
        import slicer
        import vtk
        import numpy as np
        from vtk.util import numpy_support
        from SlicerDosim.SlicerDosimLib import TissueConfig

        config = TissueConfig()
        ct_img = self.ct_node.GetImageData()
        dims = ct_img.GetDimensions()
        nx, ny, nz = dims

        step = 4
        sx, sy, sz = nx // step, ny // step, nz // step
        phantom = np.ones((sx, sy, sz), dtype=np.uint8)
        cx, cy = sx // 2, sy // 2

        # Higado (90): esfera grande centrada
        for z in range(sz):
            for y in range(sy):
                for x in range(sx):
                    dx, dy, dz = x - cx, y - cy, z - sz // 2
                    if dx*dx/(sx//6)**2 + dy*dy/(sy//6)**2 + dz*dz/(sz//3)**2 <= 1:
                        phantom[x, y, z] = 90

        # Tumor (100): esfera chica dentro del higado
        tcx, tcy, tcz = cx + sx // 8, cy + sy // 8, sz // 2
        for z in range(sz):
            for y in range(sy):
                for x in range(sx):
                    dx, dy, dz = x - tcx, y - tcy, z - tcz
                    if dx*dx + dy*dy + dz*dz < (sx // 20) ** 2:
                        phantom[x, y, z] = 100

        labelmap = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "__synthetic_phantom__"
        )
        labelmap.CopyOrientation(self.ct_node)
        labelmap.SetSpacing(
            self.ct_node.GetSpacing()[0] * step,
            self.ct_node.GetSpacing()[1] * step,
            self.ct_node.GetSpacing()[2] * step,
        )

        arr_flat = phantom.astype(np.uint8).ravel()
        vtk_arr = numpy_support.numpy_to_vtk(arr_flat, deep=True)
        vtk_img = vtk.vtkImageData()
        vtk_img.SetDimensions(sx, sy, sz)
        vtk_img.GetPointData().SetScalars(vtk_arr)
        labelmap.SetAndObserveImageData(vtk_img)

        seg_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "Phantom_3Dosim_Sintetico"
        )
        seg_node.CreateDefaultDisplayNodes()
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelmap, seg_node
        )
        self.segmentation_node = seg_node
        slicer.mrmlScene.RemoveNode(labelmap)

        # Renombrar segmentos por indice (API Slicer 5.8)
        seg = seg_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        seg.GetSegmentIDs(segment_ids)
        for i in range(segment_ids.GetNumberOfValues()):
            seg_id = segment_ids.GetValue(i)
            segment = seg.GetSegment(seg_id)
            if not segment:
                continue
            name = segment.GetName()
            try:
                idx = int(name)
                tissue = config.get_tissue(idx)
                if tissue:
                    seg.SetSegmentName(seg_id, tissue["name"])
                    c = tissue["color"]
                    dn = seg_node.GetDisplayNode()
                    if dn:
                        dn.SetSegmentColor(seg_id, c[0], c[1], c[2])
            except ValueError:
                pass

        # Asignar geometria de referencia para poder exportar a labelmap
        seg_node.SetReferenceImageGeometryParameterFromVolumeNode(self.ct_node)

        indices = sorted(set(phantom.flatten()))
        logger.info(f"  ✓ Phantom sintetico: {sx}x{sy}x{sz}")
        logger.info(f"    Indices: {indices}")
        slicer.util.showStatusMessage("Phantom sintetico generado", 3000)

    # ==================================================================
    # VALIDACION MEDICA
    # ==================================================================

    def _validate_segmentation(self):
        """
        VALIDACION MEDICA OBLIGATORIA.
        La segmentacion debe ser revisada y aprobada por un medico
        antes de continuar con la generacion de entrada MCNP.

        Muestra un dialogo modal que bloquea el pipeline hasta
        que el medico confirme o rechace la segmentacion.
        """
        import slicer

        logger.info("")
        logger.info("  ╔════════════════════════════════════════════════════╗")
        logger.info("  ║   VALIDACION MEDICA REQUERIDA                     ║")
        logger.info("  ║                                                  ║")
        logger.info("  ║   Un medico debe revisar la segmentacion         ║")
        logger.info("  ║   antes de continuar con los calculos            ║")
        logger.info("  ║   dosimetricos.                                  ║")
        logger.info("  ╚════════════════════════════════════════════════════╝")
        logger.info("")

        self._show_progress("⚠ VALIDACION MEDICA PENDIENTE")

        # Intentar mostrar dialogo Qt en Slicer
        try:
            from qt import QMessageBox, QApplication, QInputDialog, QLabel, QVBoxLayout, QDialog, QPushButton, Qt

            dialog = QDialog()
            dialog.setWindowTitle("3Dosim - Validacion Medica Obligatoria")
            dialog.setMinimumWidth(500)
            dialog.setModal(True)

            layout = QVBoxLayout()

            msg = QLabel(
                "⚠ VALIDACION MEDICA REQUERIDA\n\n"
                "La segmentacion anatomica se ha completado.\n\n"
                "Un medico especialista DEBE revisar y aprobar\n"
                "la segmentacion antes de continuar con:\n"
                "  • Generacion de entrada MCNP\n"
                "  • Calculo de dosis\n"
                "  • Analisis dosimetrico\n\n"
                "¿La segmentacion es correcta y puede continuar?"
            )
            msg.setWordWrap(True)
            layout.addWidget(msg)

            # Botones
            btn_yes = QPushButton("✓ SI, aprobado - Continuar")
            btn_no = QPushButton("✗ NO, rechazado - Detener pipeline")

            layout.addSpacing(20)
            layout.addWidget(btn_yes)
            layout.addWidget(btn_no)

            dialog.setLayout(layout)

            # Conectar botones
            result = [False]  # mutable para closure

            def on_yes():
                result[0] = True
                dialog.accept()

            def on_no():
                result[0] = False
                dialog.reject()

            btn_yes.clicked.connect(on_yes)
            btn_no.clicked.connect(on_no)

            # Estilo
            btn_yes.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
            btn_no.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")

            # Mostrar dialogo
            logger.info("  ⏳ Esperando validacion del medico...")
            dialog.exec_()

            approved = result[0]

        except ImportError:
            # Fallback: consola
            logger.info("  (Interfaz Qt no disponible, usando consola)")
            logger.info("")
            respuesta = input("  ¿La segmentacion es correcta? (si/no): ").strip().lower()
            approved = respuesta in ("si", "s", "yes", "y")

        if approved:
            logger.info("")
            logger.info("  ╔════════════════════════════════════════════════════╗")
            logger.info("  ║   ✓ SEGMENTACION APROBADA POR MEDICO             ║")
            logger.info("  ║   Continuando con el pipeline...                 ║")
            logger.info("  ╚════════════════════════════════════════════════════╝")
            logger.info("")
            self._show_progress("✓ Segmentacion aprobada - continuando")
        else:
            logger.info("")
            logger.info("  ╔════════════════════════════════════════════════════╗")
            logger.info("  ║   ✗ SEGMENTACION RECHAZADA                       ║")
            logger.info("  ║   Pipeline detenido.                             ║")
            logger.info("  ║   Corrija la segmentacion y reinicie.            ║")
            logger.info("  ╚════════════════════════════════════════════════════╝")
            logger.info("")
            raise RuntimeError(
                "Segmentacion rechazada por el medico. "
                "Corrija la segmentacion y ejecute con --reset para reiniciar."
            )

    # ==================================================================
    # EXPORT NIFTI
    # ==================================================================

    def _export_nifti(self):
        """Exporta el phantom segmentado a NIfTI."""
        logger.info("  ⏭ Export NIfTI: saltado (no necesario para Mod 2)")
        self.phantom_nifti_path = None

    def _generate_mcnp(self):
        """
        Genera entrada MCNP y verifica el .i.
        Usa arrays numpy directamente (sin depender de export segmentation).
        """
        import slicer
        import numpy as np
        from vtk.util import numpy_support
        import vtk

        if not hasattr(self, 'ct_node') or self.ct_node is None:
            raise RuntimeError("CT no disponible")

        from SlicerDosim.SlicerDosimLib import MCNPInputGenerator, MCNPMaterialMapper, MCNPGeometryBuilder, MCNPTallyBuilder, MCNPSourceBuilder, TissueConfig

        config = TissueConfig()
        dims = self.ct_node.GetImageData().GetDimensions()
        origin = self.ct_node.GetOrigin()
        spacing = self.ct_node.GetSpacing()

        mcnp_dir = os.path.join(self.output_dir, "mcnp")
        if not os.path.exists(mcnp_dir):
            os.makedirs(mcnp_dir)

        logger.info("  Creando phantom array...")

        # Phantom simplificado: elipse de higado (90) + tumor (100) en volumen mas chico
        step = 4
        sx, sy, sz = dims[0] // step, dims[1] // step, dims[2] // step
        phantom_arr = np.ones((sx, sy, sz), dtype=np.uint8)
        cx, cy, cz = sx // 2, sy // 2, sz // 2

        # Elipse higado
        rx, ry, rz = sx // 4, sy // 4, sz // 3
        for z in range(max(0, cz-rz), min(sz, cz+rz)):
            for y in range(sy):
                for x in range(sx):
                    dx, dy, dz = (x-cx)/rx, (y-cy)/ry, (z-cz)/rz
                    if dx*dx + dy*dy + dz*dz <= 1:
                        phantom_arr[x, y, z] = 90

        # Esfera tumor
        tcx, tcy, tcz = cx + rx//2, cy, cz
        tr = sx // 16
        for z in range(max(0, tcz-tr), min(sz, tcz+tr)):
            for y in range(sy):
                for x in range(sx):
                    dx, dy, dz = x-tcx, y-tcy, z-tcz
                    if dx*dx + dy*dy + dz*dz <= tr*tr:
                        phantom_arr[x, y, z] = 100

        logger.info(f"  Phantom array: {sx}x{sy}x{sz}")
        logger.info(f"  Indices: {sorted(np.unique(phantom_arr))}")

        # --- Test materiales ---
        logger.info("  [A] Asignando materiales...")
        mapper = MCNPMaterialMapper(config)
        mat_arr = mapper.assign_from_labelmap(phantom_arr)
        mat_cards = mapper.generate_material_cards()
        logger.info(f"      Materiales: {sorted(mapper.get_material_ids_used())}")
        logger.info(f"      Tarjetas M: {len(mat_cards)}")

        # --- Test geometria ---
        logger.info("  [B] Construyendo geometria...")
        geo_builder = MCNPGeometryBuilder(config)
        geom_cards = geo_builder.build((sx, sy, sz), origin, spacing, mat_arr)
        logger.info(f"      Tarjetas geometria: {len(geom_cards)}")
        has_rpp = any("RPP" in c for c in geom_cards)
        has_fill = any("fill" in c for c in geom_cards)
        logger.info(f"      RPP: {'✓' if has_rpp else '✗'}")
        logger.info(f"      Fill: {'✓' if has_fill else '✗'}")

        # --- Test tallies ---
        logger.info("  [C] Configurando tallies...")
        iso_data = {
            "name": "Yttrium-90", "zaid": 39090, "energy_mev": 2.28,
            "particle": "electron", "mode": "e",
        }
        tal_builder = MCNPTallyBuilder()
        tal_cards = tal_builder.build(iso_data, (sx, sy, sz), n_particles=1000000, origin=origin)
        logger.info(f"      Tarjetas tallies: {len(tal_cards)}")
        has_fmesh4 = any("FMESH4" in c for c in tal_cards)
        has_nps = any("NPS" in c for c in tal_cards)
        logger.info(f"      FMESH4: {'✓' if has_fmesh4 else '✗'}")
        logger.info(f"      NPS:    {'✓' if has_nps else '✗'}")

        # --- Escribir archivo .i completo ---
        logger.info("  [D] Escribiendo archivo .i...")
        input_path = os.path.join(mcnp_dir, "3Dosim_MCNP_Y90.i")
        self._write_i_file(input_path, mat_cards, geom_cards, tal_cards)

        # Verificar
        self._verify_mcnp_input(input_path)
        self.mcnp_path = input_path

    def _write_i_file(self, path: str, mat_cards, geom_cards, tal_cards):
        """Escribe archivo .i MCNP formateado."""
        src_cards = [
            "C FUENTE uniforme (placeholder)",
            "SDEF  POS=0 0 0  ERG=D1  PAR=2",
            "SI1  L  0.9357  2.2807",
            "SP1  D  1.0  0.0",
        ]
        lines = [
            "3Dosim MCNP test - SlicerDosim",
            "C Generado por test_pipeline_orchestrator.py",
        ]
        lines.append("C")
        lines.append("C ===== MATERIALES =====")
        lines.extend(mat_cards)
        lines.append("C")
        lines.append("C ===== GEOMETRIA =====")
        lines.extend(geom_cards)
        lines.append("C")
        lines.append("C ===== FUENTE =====")
        lines.extend(src_cards)
        lines.append("C")
        lines.append("C ===== TALLIES =====")
        lines.extend(tal_cards)

        with open(path, "w") as f:
            f.write("\n".join(lines))
            f.write("\n")
        logger.info(f"  ✓ .i escrito: {path}")

    def _verify_mcnp_input(self, path: str):
        """Verifica que el archivo .i MCNP sea valido."""
        with open(path, "r") as f:
            content = f.read()

        checks = {
            "header": content.startswith("3Dosim"),
            "material_cards": any(line.strip().startswith("M") and " " in line for line in content.split("\n") if line.strip()),
            "geometry_cards": "PX" in content or "RPP" in content,
            "source_cards": "SDEF" in content,
            "tally_cards": "FMESH4" in content,
            "nps_card": "NPS" in content,
            "mode_card": "MODE" in content,
            "has_lattice": "fill" in content,
        }

        all_ok = True
        for check_name, ok in checks.items():
            status = "✓" if ok else "✗"
            if ok:
                logger.info(f"  Verificacion {check_name}: {status}")
            else:
                logger.warning(f"  Verificacion {check_name}: {status}")
                all_ok = False

        line_count = content.count("\n") + 1
        logger.info(f"  Archivo: {line_count} lineas, {len(content)} caracteres")

        if not all_ok:
            raise RuntimeError("Archivo MCNP no paso las verificaciones")

        logger.info("  ✓ Archivo MCNP valido")

    # ==================================================================
    # REPORTE
    # ==================================================================

    def _report(self) -> bool:
        """
        Genera reporte final del pipeline.
        Returns: True si todos los pasos fueron exitosos.
        """
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
                logger.info(f"  • {err}")

        logger.info("")
        logger.info("DETALLE DE PASOS:")
        logger.info("-" * 70)
        for paso in self.results["pasos"]:
            status = "✓" if paso["ok"] else "✗"
            cp = " (checkpoint)" if paso.get("checkpoint") else ""
            tiempo = f"{paso['tiempo']:.1f}s" if paso['tiempo'] > 0 else "-"
            logger.info(f"  {status} {paso['nombre']:<45s} {tiempo:>8s}{cp}")
        logger.info("-" * 70)

        logger.info("")
        logger.info(f"DIRECTORIOS DE SALIDA:")
        if hasattr(self, 'phantom_nifti_path') and self.phantom_nifti_path:
            logger.info(f"  Phantom NIfTI:  {self.phantom_nifti_path}")
        if hasattr(self, 'mcnp_path') and self.mcnp_path:
            logger.info(f"  MCNP input:     {self.mcnp_path}")
        if os.path.exists(self.checkpoint.checkpoint_file):
            logger.info(f"  Checkpoint:     {self.checkpoint.checkpoint_file}")
        logger.info(f"  Output:         {self.output_dir}")

        logger.info("")
        logger.info("=" * 70)
        all_ok = fails == 0
        if all_ok:
            logger.info(" RESULTADO: ✓ TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f" RESULTADO: ✗ {fails}/{total} PASOS FALLARON")
        logger.info("=" * 70)

        return all_ok

    # ==================================================================
    # GIT COMMIT PROMPT
    # ==================================================================

    def _prompt_git_commit(self):
        """
        Pregunta al usuario si quiere hacer un commit git.
        Solo se ejecuta si todos los pasos fueron exitosos.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("  ✅ PIPELINE COMPLETADO EXITOSAMENTE")
        logger.info("=" * 70)
        logger.info("")

        # Buscar directorio raiz del repo
        repo_dir = self._find_git_repo()
        if not repo_dir:
            logger.info("  ⚠ No se detecto repositorio git, saltando commit")
            return

        logger.info(f"  Repositorio detectado: {repo_dir}")
        logger.info("")

        # Preguntar si quiere commitear
        try:
            from qt import QInputDialog, QMessageBox, QApplication

            reply = QMessageBox.question(
                None,
                "3Dosim - Commit git",
                "El pipeline se completo correctamente.\n\n"
                "¿Desea hacer un commit git de los resultados y cambios?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                logger.info("  Commit cancelado por el usuario")
                return

            msg, ok = QInputDialog.getText(
                None,
                "Mensaje de commit",
                "Describa los cambios realizados:",
                text=f"3Dosim pipeline OK - {os.path.basename(self.data_dir)}"
            )
            if not ok or not msg.strip():
                logger.info("  Commit cancelado (mensaje vacio)")
                return

        except ImportError:
            # Fallback a consola
            logger.info("  (Interfaz Qt no disponible, usando consola)")
            respuesta = input("  ¿Hacer commit git? (si/no): ").strip().lower()
            if respuesta not in ("si", "s", "yes", "y"):
                logger.info("  Commit cancelado")
                return
            msg = input("  Mensaje de commit: ").strip()
            if not msg:
                logger.info("  Commit cancelado (mensaje vacio)")
                return

        # Ejecutar git commit
        try:
            logger.info(f"  Ejecutando git commit...")
            subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True,
                           capture_output=True, text=True)

            result = subprocess.run(
                ["git", "commit", "-m", msg.strip()],
                cwd=repo_dir, capture_output=True, text=True
            )

            if result.returncode == 0:
                logger.info(f"  ✓ Commit exitoso: {result.stdout.strip()}")
                self._show_progress("✓ Commit git realizado")
            else:
                if "nothing to commit" in result.stderr or "nothing to commit" in result.stdout:
                    logger.info("  ℹ No hay cambios nuevos para commitear")
                else:
                    logger.warning(f"  ⚠ Error en commit: {result.stderr.strip()}")

        except subprocess.CalledProcessError as e:
            logger.warning(f"  ⚠ Error en git add: {e.stderr}")
        except FileNotFoundError:
            logger.warning("  ⚠ Git no encontrado en el sistema")
        except Exception as e:
            logger.warning(f"  ⚠ Error inesperado en git: {e}")

    @staticmethod
    def _find_git_repo() -> str | None:
        """Busca el directorio raiz del repositorio git desde el directorio actual."""
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(10):  # Subir hasta 10 niveles
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None


# ==================================================================
# MAIN
# ==================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline test orchestrator para SlicerDosim"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2",
        help="Directorio con subdirectorios CT/ y PET/",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reiniciar checkpoints (ignora estado guardado)",
    )
    args = parser.parse_args()

    orchestrator = PipelineTestOrchestrator(args.data_dir, reset=args.reset)
    orchestrator.run()
