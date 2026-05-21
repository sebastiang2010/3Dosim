"""
Pipeline de Fusion PET/CT - 3Dosim v3.14
Flujo completo: carga DICOM → preprocessing → registro (2 métodos) → fusión visual → reporte.

Dos métodos de registro:
  A - ResampleScalarVolume (CLI de Slicer)
  B - NumPy interp3 con conservación de actividad

El pipeline retoma desde checkpoints si se corta (--reset para empezar fresco).
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Agregar Testing/ al path para importar PipelineOrchestrator como paquete
_script_dir = os.path.dirname(os.path.abspath(__file__))          # .../PipelineOrchestrator/
_testing_dir = os.path.dirname(_script_dir)                       # .../Testing/
if _testing_dir not in sys.path:
    sys.path.insert(0, _testing_dir)

logger = logging.getLogger("3DosimFusion")


# ============================================================================
# CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager:
    """Estado persistente del pipeline. Retoma desde donde quedó si se corta."""

    VERSION = 1

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = os.path.join(checkpoint_dir, "fusion_checkpoint.json")
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file) as f:
                    state = json.load(f)
                if state.get("version") == self.VERSION:
                    return state
            except (json.JSONDecodeError, KeyError):
                pass
        return {"version": self.VERSION, "completed": [], "data": {}}

    def is_completed(self, step: str) -> bool:
        return step in self.state["completed"]

    def mark_completed(self, step: str, data: dict = None):
        if step not in self.state["completed"]:
            self.state["completed"].append(step)
        if data:
            self.state["data"][step] = data
        self._save()

    def get_data(self, step: str) -> dict:
        return self.state["data"].get(step, {})

    def _save(self):
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        with open(self.checkpoint_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def reset(self):
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        self.state = {"version": self.VERSION, "completed": [], "data": {}}
        logger.info("  Checkpoints reiniciados")


# ============================================================================
# PIPELINE
# ============================================================================

class FusionPipeline:
    """
    Pipeline de fusión PET/CT con 2 métodos de registro.

    Args:
        data_dir: Directorio con subcarpetas CT/ y PET/
        output_dir: Donde guardar resultados
        reset: True para reiniciar checkpoints
    """

    # Nombres de pasos (claves en checkpoint)
    STEP_CHECK_SLICER    = "check_slicer"
    STEP_LOAD_DICOM      = "load_dicom"
    STEP_REMOVE_COUCH    = "remove_couch_air"
    STEP_REGISTER_A      = "register_method_a"   # ResampleScalarVolume
    STEP_REGISTER_B      = "register_method_b"   # NumPy interp3
    STEP_COMPARE         = "compare_methods"
    STEP_SHOW_FUSION     = "show_fusion"
    STEP_REPORT          = "report"

    def __init__(self, data_dir: str, output_dir: str = None, reset: bool = False):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")

        if output_dir is None:
            self.output_dir = os.path.join(data_dir, "..", "resultados_fusion")
        else:
            self.output_dir = output_dir

        self.checkpoint_dir = os.path.join(self.output_dir, ".checkpoints")
        self.screenshots_dir = os.path.join(self.output_dir, "screenshots")
        self.scenes_dir = os.path.join(self.output_dir, "scenes")
        self.checkpoint = CheckpointManager(self.checkpoint_dir)

        if reset:
            self.checkpoint.reset()

        # Nodos Slicer
        self.ct_node = None
        self.ct_masked_node = None   # CT sin camilla
        self.pet_node = None
        self.pet_reg_a_node = None   # Método A
        self.pet_reg_b_node = None   # Método B
        self.phantom_node = None

        # Resultados de cada método
        self.result_a = None
        self.result_b = None
        self.comparison = None

        # Estadísticas
        self.step_results = []
        self.screenshots = []

        logger.info("=" * 60)
        logger.info(" Pipeline Fusion PET/CT v3.14")
        logger.info("=" * 60)
        logger.info(f"Datos:       {self.data_dir}")
        logger.info(f"Output:      {self.output_dir}")
        logger.info(f"Reset:       {'SI' if reset else 'NO'}")
        logger.info("")

    # ------------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------------

    def run(self):
        logger.info("")
        logger.info("INICIANDO PIPELINE DE FUSION PET/CT")
        logger.info("")

        # -- Verificar Slicer --
        if not self._checkpoint_step(self.STEP_CHECK_SLICER,
                                     "Verificando entorno Slicer",
                                     self._check_slicer):
            logger.error("Fallo: no se detecta 3D Slicer")
            return

        # -- Cargar DICOM --
        if not self._checkpoint_step(self.STEP_LOAD_DICOM,
                                     "Cargando DICOM (CT + PET)",
                                     self._load_dicom,
                                     data_func=lambda: {
                                         "ct_name": self.ct_node.GetName() if self.ct_node else None,
                                         "pet_name": self.pet_node.GetName() if self.pet_node else None,
                                     }):
            logger.error("Fallo crítico en carga DICOM. Abortando.")
            self._report()
            return

        # self._save_scene("01_post_load_dicom")  # comentado: saveScene rompe display pipeline
        self._screenshot("01_carga_dicom")

        # -- Eliminar camilla y aire del CT --
        if not self._checkpoint_step(self.STEP_REMOVE_COUCH,
                                     "Eliminando camilla y aire del CT",
                                     self._remove_couch_air):
            logger.warning("No se pudo eliminar camilla, continuando con CT original")

        # self._save_scene("02_remove_couch")  # comentado: saveScene rompe display pipeline
        self._screenshot("02_remove_couch")

        # -- Registro Método A: ResampleScalarVolume --
        if not self._checkpoint_step(self.STEP_REGISTER_A,
                                     "Registro PET -> CT (Metodo A: ResampleScalarVolume)",
                                     self._register_method_a,
                                     data_func=lambda: {
                                         "dims": self.result_a.get("dimensions") if self.result_a else None,
                                         "spacing": self.result_a.get("spacing") if self.result_a else None,
                                         "activity": self.result_a.get("total_activity_bq") if self.result_a else None,
                                         "duration": self.result_a.get("duration_s") if self.result_a else None,
                                     }):
            logger.warning("Método A falló, se usará solo Método B si funciona")

        # -- Registro Método B: NumPy interp3 --
        if not self._checkpoint_step(self.STEP_REGISTER_B,
                                     "Registro PET -> CT (Metodo B: NumPy interp3)",
                                     self._register_method_b,
                                     data_func=lambda: {
                                         "dims": self.result_b.get("dimensions") if self.result_b else None,
                                         "spacing": self.result_b.get("spacing") if self.result_b else None,
                                         "activity": self.result_b.get("total_activity_bq") if self.result_b else None,
                                         "duration": self.result_b.get("duration_s") if self.result_b else None,
                                     }):
            logger.warning("Método B falló")

        # -- Comparar ambos métodos --
        if self.result_a and self.result_b:
            self._checkpoint_step(self.STEP_COMPARE,
                                  "Comparando metodos de registro A vs B",
                                  self._compare_methods,
                                  data_func=lambda: {
                                      "mae": self.comparison.get("mae") if self.comparison else None,
                                      "rmse": self.comparison.get("rmse") if self.comparison else None,
                                  })
        else:
            logger.info("  Saltando comparación: solo un método disponible")

        # -- Fusión visual --
        if not self._checkpoint_step(self.STEP_SHOW_FUSION,
                                     "Mostrando fusion visual CT + PET",
                                     self._show_fusion):
            logger.warning("Fusión visual falló")

        self._screenshot("03_fusion")

        # -- Reporte final --
        self._checkpoint_step(self.STEP_REPORT,
                              "Generando reporte final",
                              self._report)

    # ------------------------------------------------------------------
    # PASOS DEL PIPELINE
    # ------------------------------------------------------------------

    def _check_slicer(self):
        try:
            import slicer
            ver = f"{slicer.app.majorVersion}.{slicer.app.minorVersion}"
            logger.info(f"  Slicer versión: {ver}")
        except ImportError:
            raise RuntimeError("Ejecutar dentro de 3D Slicer (--python-script)")

    def _load_dicom(self):
        """Carga CT y PET desde disco usando DICOMUtils."""
        import slicer
        from DICOMLib import DICOMUtils

        # Verificar directorios
        for d, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio {label} no encontrado: {d}")
            archivos = [f for f in os.listdir(d) if f.endswith('.dcm') or f.isdigit()]
            logger.info(f"  {label}: {len(archivos)} archivos DICOM")

        # Indexar en DB temporal
        db_dir = DICOMUtils.openTemporaryDatabase()
        try:
            for d in [self.ct_dir, self.pet_dir]:
                ok = DICOMUtils.importDicom(d)
                if not ok:
                    raise RuntimeError(f"Fallo al indexar: {d}")

            uids = DICOMUtils.allSeriesUIDsInDatabase()
            if not uids:
                raise RuntimeError("No se encontraron series DICOM")
            logger.info(f"  Series encontradas: {len(uids)}")

            nodos = DICOMUtils.loadSeriesByUID(uids)
            logger.info(f"  Nodos cargados: {len(nodos)}")
        finally:
            DICOMUtils.closeTemporaryDatabase(db_dir, cleanup=True)

        # Identificar CT y PET por nombre
        for nid in nodos:
            node = slicer.mrmlScene.GetNodeByID(nid)
            if not node:
                continue
            name = node.GetName().upper()
            if "CT" in name and self.ct_node is None:
                self.ct_node = node
            elif any(k in name for k in ["PET", "PT", "NM"]) and self.pet_node is None:
                self.pet_node = node

        # Fallbacks si no se identificó por nombre
        if self.ct_node is None and nodos:
            self.ct_node = slicer.mrmlScene.GetNodeByID(nodos[0])

        if self.pet_node is None and len(nodos) > 1:
            for nid in nodos:
                node = slicer.mrmlScene.GetNodeByID(nid)
                if node and node != self.ct_node:
                    self.pet_node = node
                    break

        if self.ct_node is None:
            raise RuntimeError("No se pudo cargar volumen CT")
        if self.pet_node is None:
            logger.warning("  PET no encontrado — se usará fuente sintética")

        # Mostrar info
        dims = self.ct_node.GetImageData().GetDimensions()
        spc = self.ct_node.GetSpacing()
        logger.info(f"  CT cargado: {dims[0]}x{dims[1]}x{dims[2]}, {spc[0]:.2f}x{spc[1]:.2f}x{spc[2]:.2f} mm")
        if self.pet_node:
            pdims = self.pet_node.GetImageData().GetDimensions()
            pspc = self.pet_node.GetSpacing()
            logger.info(f"  PET cargado: {pdims[0]}x{pdims[1]}x{pdims[2]}, {pspc[0]:.2f}x{pspc[1]:.2f}x{pspc[2]:.2f} mm")

    def _remove_couch_air(self):
        """Elimina camilla y aire del CT (threshold HU > -200 + morfología)."""
        import slicer
        import numpy as np
        import vtk
        from vtk.util import numpy_support
        from scipy import ndimage as ndi

        logger.info("  Eliminando camilla y aire del CT...")

        arr = slicer.util.arrayFromVolume(self.ct_node)       # (K, J, I)
        spacing = self.ct_node.GetSpacing()

        # Threshold: HU > -200 (elimina aire)
        mask = arr > -200

        # Cierre morfológico para rellenar huecos
        mask = ndi.binary_closing(mask, structure=np.ones((3, 3, 3)), iterations=2)

        # Componente conectada más grande (cuerpo del paciente)
        labels, n_labels = ndi.label(mask)
        if n_labels > 0:
            sizes = np.bincount(labels.ravel())
            sizes[0] = 0       # fondo
            largest = sizes.argmax()
            mask = labels == largest

        # Eliminar camilla: buscar último slice axial con >30% del área máxima
        # y cortar todo lo que esté por debajo
        try:
            nk, nj, ni = mask.shape
            areas = mask.sum(axis=(1, 2))                     # área por slice
            max_area = areas.max()
            if max_area > 0:
                # Encontrar slices que son >30% del área máxima
                above_thresh = np.where(areas > 0.3 * max_area)[0]
                if len(above_thresh) > 0:
                    last_body_slice = above_thresh[-1]
                    # Desde el último slice del cuerpo hacia abajo buscar la camilla
                    # La camilla aparece como área pequeña debajo del cuerpo
                    for k in range(last_body_slice, nk):
                        if areas[k] < 0.15 * max_area and k > last_body_slice:
                            # A partir de este slice, todo es camilla
                            mask[k:] = False
                            break

        except Exception as e:
            logger.warning(f"  Error en eliminación de camilla: {e}")

        # Aplicar máscara al CT: donde mask=False poner HU=-1024 (aire)
        arr_masked = arr.copy()
        arr_masked[~mask] = -1024

        # Crear nodo Slicer con el CT sin camilla/aire
        ct_masked = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeNode", "CT_sin_camilla"
        )

        # Copiar geometría del CT original
        ijk_to_ras = vtk.vtkMatrix4x4()
        self.ct_node.GetIJKToRASMatrix(ijk_to_ras)
        ct_masked.SetIJKToRASMatrix(ijk_to_ras)
        ct_masked.SetSpacing(self.ct_node.GetSpacing())
        ct_masked.SetOrigin(self.ct_node.GetOrigin())

        # Convertir numpy -> vtk
        arr_trans = np.transpose(arr_masked, (2, 1, 0)).astype(np.int16)
        flat = arr_trans.ravel(order='C')
        vtk_arr = numpy_support.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_SHORT)

        vtk_img = vtk.vtkImageData()
        vtk_img.SetDimensions(self.ct_node.GetImageData().GetDimensions())
        vtk_img.SetSpacing(self.ct_node.GetSpacing())
        vtk_img.SetOrigin(self.ct_node.GetOrigin())
        vtk_img.GetPointData().SetScalars(vtk_arr)
        ct_masked.SetAndObserveImageData(vtk_img)

        # Display node
        dn = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeDisplayNode")
        dn.SetDefaultColorMap()
        ct_masked.SetAndObserveDisplayNodeID(dn.GetID())

        self.ct_masked_node = ct_masked
        logger.info("  CT sin camilla/aire creado OK")

    def _register_method_a(self):
        """Método A: ResampleScalarVolume (CLI de Slicer)."""
        import slicer
        import numpy as np

        logger.info("  ┌─────────────────────────────────────────────┐")
        logger.info("  │ Método A: ResampleScalarVolume (CLI Slicer) │")
        logger.info("  └─────────────────────────────────────────────┘")

        from PipelineOrchestrator.pet_registration import register_pet_slicer
        self.result_a = register_pet_slicer(self.ct_node, self.pet_node, self.output_dir)
        self.pet_reg_a_node = self.result_a.get("node")

        if self.result_a.get("success"):
            logger.info(f"  ✔ Método A completado en {self.result_a['duration_s']:.1f}s")
            logger.info(f"    Actividad: {self.result_a['total_activity_bq']:.2e}")
        else:
            error_msg = self.result_a.get('error', 'desconocido')
            logger.error(f"  ✘✘✘ MÉTODO A FALLÓ ✘✘✘")
            logger.error(f"     Error: {error_msg}")
            logger.error(f"     Causa posible: módulo ResampleScalarVolume no disponible")
            logger.error(f"     El pipeline continuará con Método B (NumPy)")
            raise RuntimeError(error_msg)

    def _register_method_b(self):
        """Método B: NumPy interp3 con conservación de actividad."""
        logger.info("  ┌─────────────────────────────────────────────┐")
        logger.info("  │ Método B: NumPy interp3 + conservación     │")
        logger.info("  └─────────────────────────────────────────────┘")

        from PipelineOrchestrator.pet_registration import register_pet_numpy
        self.result_b = register_pet_numpy(self.ct_node, self.pet_node, self.output_dir)
        self.pet_reg_b_node = self.result_b.get("node")

        if self.result_b.get("success"):
            logger.info(f"  ✔ Método B completado en {self.result_b['duration_s']:.1f}s")
            logger.info(f"    Actividad: {self.result_b['total_activity_bq']:.2e}")
        else:
            error_msg = self.result_b.get('error', 'desconocido')
            logger.error(f"  ✘✘✘ MÉTODO B FALLÓ ✘✘✘")
            logger.error(f"     Error: {error_msg}")
            raise RuntimeError(error_msg)

    def _compare_methods(self):
        """Compara resultados A vs B y selecciona el mejor."""
        from PipelineOrchestrator.pet_registration import compare_registration, select_best_result

        self.comparison = compare_registration(self.result_a, self.result_b)
        self.best_result = select_best_result(self.result_a, self.result_b)

        logger.info(f"  Mejor método: {self.best_result.get('method', 'N/A')}")
        logger.info(f"  MAE entre métodos: {self.comparison.get('mae', 'N/A')}")

    def _show_fusion(self):
        """Muestra fusión CT (fondo) + PET original (foreground, 35%).
        Asigna volúmenes directamente a los composite nodes de cada slice."""
        import slicer
        import numpy as np

        logger.info("  Configurando vista de fusión CT+PET...")

        bg = self.ct_node
        fg = self.pet_node

        if bg is None:
            logger.error("  No hay CT para mostrar")
            return

        # -------------------------------------------------------
        # 1. LAYOUT 4-UP
        # -------------------------------------------------------
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
        slicer.app.processEvents()

        # -------------------------------------------------------
        # 2. CONFIGURAR DISPLAY NODES
        #    (Crear si no existen — en script a veces no se crean solos)
        # -------------------------------------------------------
        for node in [bg, fg]:
            if node is None:
                continue
            if not node.GetDisplayNode():
                node.CreateDefaultDisplayNodes()

        # CT: window/level
        bg_dn = bg.GetDisplayNode()
        if bg_dn:
            bg_dn.AutoWindowLevelOff()
            bg_dn.SetWindowLevel(400.0, 40.0)

        # PET: Rainbow colormap + auto WL
        if fg:
            fg_dn = fg.GetDisplayNode()
            if fg_dn:
                fg_dn.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRainbow")
                fg_dn.AutoWindowLevelOff()
                try:
                    arr = slicer.util.arrayFromVolume(fg)
                    if arr is not None and arr.size > 0:
                        pos = arr[arr > 0]
                        if len(pos) > 100:
                            p95 = float(np.percentile(pos, 95))
                            p05 = float(np.percentile(pos, 5))
                            ww = max(p95 - p05, 1.0)
                            wl = p05 + ww / 2.0
                            fg_dn.SetWindowLevel(ww, wl)
                        else:
                            fg_dn.SetWindowLevel(40.0, 20.0)
                except Exception:
                    fg_dn.SetWindowLevel(40.0, 20.0)

        # -------------------------------------------------------
        # 3. ASIGNAR VOLUMENES A CADA SLICE COMPOSITE NODE
        #    (mas directo que setSliceViewerLayers)
        # -------------------------------------------------------
        for nombre in ["RED", "YELLOW", "GREEN"]:
            try:
                sw = lm.sliceWidget(nombre)
                if not sw:
                    continue
                cn = sw.mrmlSliceCompositeNode()
                cn.SetBackgroundVolumeID(bg.GetID())
                if fg:
                    cn.SetForegroundVolumeID(fg.GetID())
                    cn.SetForegroundOpacity(0.35)
                else:
                    cn.SetForegroundVolumeID(None)
                    cn.SetForegroundOpacity(0.0)
                # Forzar actualizacion del slice node
                sn = sw.mrmlSliceNode()
                sn.UpdateMatrices()
            except Exception as e:
                logger.debug(f"  Error configurando slice {nombre}: {e}")

        # -------------------------------------------------------
        # 4. REFRESCAR
        # -------------------------------------------------------
        slicer.app.processEvents()
        for nombre in ["RED", "YELLOW", "GREEN"]:
            try:
                sw = lm.sliceWidget(nombre)
                if sw:
                    sw.sliceView().scheduleRender()
            except Exception:
                pass
        slicer.app.processEvents()

        logger.info(f"  Fusión: CT 'fondo' + PET 'foreground' 35%")
        if fg:
            logger.info("  PET colormap: Rainbow")

        # Guardar escena DESPUES de configurar la fusion (no antes)
        self._save_scene("03_fusion_ct_pet")

    # ------------------------------------------------------------------
    # CHECKPOINT STEP
    # ------------------------------------------------------------------

    def _checkpoint_step(self, step_name, display_name, func, data_func=None):
        """Ejecuta un paso con checkpoint. Si ya está completado, salta."""
        if self.checkpoint.is_completed(step_name):
            logger.info(f"  [checkpoint] {display_name} — ya completado, saltando")
            self.step_results.append({"nombre": display_name, "ok": True, "checkpoint": True})
            cp_data = self.checkpoint.get_data(step_name)
            if cp_data:
                self._restore_state(step_name, cp_data)
            return True

        logger.info(f"▶ {display_name}...")
        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  ✔ {display_name} — {elapsed:.1f}s")
            self.step_results.append({"nombre": display_name, "ok": True, "tiempo": elapsed})
            data = data_func() if data_func else {}
            self.checkpoint.mark_completed(step_name, data=data)
            return True
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  ✘ {display_name} — FALLO: {e}")
            self.step_results.append({"nombre": display_name, "ok": False, "tiempo": elapsed})
            return False

    def _restore_state(self, step_name, data):
        """Restaura atributos desde datos de checkpoint."""
        if not data:
            return
        import slicer

        # Mapeo: clave_checkpoint -> atributo
        node_map = {
            "ct_name": "ct_node",
            "pet_name": "pet_node",
        }
        for key, attr in node_map.items():
            name = data.get(key)
            if name:
                try:
                    node = slicer.util.getNode(name)
                    setattr(self, attr, node)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # HELPERS: escenas, screenshots, reporte
    # ------------------------------------------------------------------

    def _save_scene(self, tag):
        """Guarda escena Slicer como .mrb."""
        try:
            import slicer
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"fusion_scene_{tag}_{ts}.mrb"
            fpath = os.path.join(self.scenes_dir, fname)
            os.makedirs(self.scenes_dir, exist_ok=True)
            ok = slicer.util.saveScene(fpath)
            if ok:
                logger.info(f"  Escena guardada: {fname}")
        except Exception as e:
            logger.warning(f"  No se guardó escena: {e}")

    def _screenshot(self, nombre):
        """Toma screenshot de la vista 3D."""
        try:
            import slicer
            ts = datetime.now().strftime("%H%M%S")
            fname = f"{ts}_{nombre}.png"
            fpath = os.path.join(self.screenshots_dir, fname)
            os.makedirs(self.screenshots_dir, exist_ok=True)

            lm = slicer.app.layoutManager()
            if lm:
                view = lm.threeDWidget(0).threeDView()
                pixmap = view.grab()
                pixmap.save(fpath)
                self.screenshots.append(fpath)
                logger.info(f"  Screenshot: {fname}")
        except Exception as e:
            logger.warning(f"  Screenshot falló: {e}")

    def _save_results_json(self):
        """Persiste resultados en JSON."""
        results_file = os.path.join(self.output_dir, "fusion_results.json")
        historial = []
        if os.path.exists(results_file):
            try:
                with open(results_file) as f:
                    historial = json.load(f)
                    if not isinstance(historial, list):
                        historial = [historial]
            except Exception:
                historial = []

        ok = sum(1 for s in self.step_results if s["ok"])
        total = len(self.step_results)

        registro = {
            "fecha": datetime.now().isoformat(),
            "data_dir": self.data_dir,
            "output_dir": self.output_dir,
            "total_pasos": total,
            "exitosos": ok,
            "resultado": "OK" if ok == total else "ERROR",
            "pasos": self.step_results,
            "metodo_a": self.result_a.get("method") if self.result_a else None,
            "metodo_a_ok": self.result_a.get("success") if self.result_a else False,
            "metodo_a_actividad": self.result_a.get("total_activity_bq") if self.result_a else None,
            "metodo_a_duracion": self.result_a.get("duration_s") if self.result_a else None,
            "metodo_b": self.result_b.get("method") if self.result_b else None,
            "metodo_b_ok": self.result_b.get("success") if self.result_b else False,
            "metodo_b_actividad": self.result_b.get("total_activity_bq") if self.result_b else None,
            "metodo_b_duracion": self.result_b.get("duration_s") if self.result_b else None,
            "comparacion_mae": self.comparison.get("mae") if self.comparison else None,
            "comparacion_rmse": self.comparison.get("rmse") if self.comparison else None,
            "screenshots": self.screenshots,
        }

        historial.append(registro)
        with open(results_file, "w") as f:
            json.dump(historial, f, indent=2, default=str)
        logger.info(f"  Resultados guardados en: {results_file}")

    def _report(self):
        """Reporte final del pipeline."""
        try:
            self._save_results_json()
        except Exception as e:
            logger.warning(f"  No se guardó results.json: {e}")

        logger.info("")
        logger.info("=" * 70)
        logger.info(" REPORTE FINAL — PIPELINE DE FUSION PET/CT")
        logger.info("=" * 70)

        total = len(self.step_results)
        ok = sum(1 for s in self.step_results if s["ok"])
        fails = total - ok
        skipped = sum(1 for s in self.step_results if s.get("checkpoint"))

        logger.info(f"  Pasos totales:        {total}")
        logger.info(f"  Exitosos:             {ok}")
        logger.info(f"  Desde checkpoint:     {skipped}")
        logger.info(f"  Fallos:               {fails}")

        logger.info("")
        logger.info("  DETALLE DE PASOS:")
        logger.info("  " + "-" * 60)
        for s in self.step_results:
            ok_sym = "✔" if s["ok"] else "✘"
            cp = " (checkpoint)" if s.get("checkpoint") else ""
            t = f"{s['tiempo']:.1f}s" if s.get("tiempo") else "-"
            logger.info(f"    {ok_sym} {s['nombre']:<50s} {t:>8s}{cp}")

        logger.info("")
        logger.info("  RESULTADOS DE REGISTRO:")
        if self.result_a:
            logger.info(f"    Método A ({self.result_a.get('method')}):")
            logger.info(f"      Estado:    {'OK' if self.result_a.get('success') else 'FALLO'}")
            logger.info(f"      Duración:  {self.result_a.get('duration_s', 0):.1f}s")
            logger.info(f"      Actividad: {self.result_a.get('total_activity_bq', 0):.2e}")
        if self.result_b:
            logger.info(f"    Método B ({self.result_b.get('method')}):")
            logger.info(f"      Estado:    {'OK' if self.result_b.get('success') else 'FALLO'}")
            logger.info(f"      Duración:  {self.result_b.get('duration_s', 0):.1f}s")
            logger.info(f"      Actividad: {self.result_b.get('total_activity_bq', 0):.2e}")
        if self.comparison:
            logger.info(f"    Comparación A vs B:")
            logger.info(f"      MAE:     {self.comparison.get('mae', 'N/A')}")
            logger.info(f"      RMSE:    {self.comparison.get('rmse', 'N/A')}")
            logger.info(f"      Max diff: {self.comparison.get('max_diff', 'N/A')}")
        if hasattr(self, 'best_result') and self.best_result:
            logger.info(f"    Mejor método: {self.best_result.get('method', 'N/A')}")

        logger.info("")
        logger.info(f"  Directorios de salida:")
        logger.info(f"    Screenshots: {self.screenshots_dir}")
        logger.info(f"    Escenas:     {self.scenes_dir}")
        logger.info(f"    Checkpoints: {self.checkpoint_dir}")

        logger.info("")
        all_ok = fails == 0
        if all_ok:
            logger.info("  RESULTADO: TODOS LOS PASOS EXITOSOS ✔")
        else:
            logger.info(f"  RESULTADO: {fails}/{total} PASOS FALLARON ✘")
        logger.info("=" * 70)

        return all_ok


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de Fusion PET/CT para 3Dosim"
    )
    parser.add_argument("--data-dir", type=str, required=True,
                        help="Directorio con subcarpetas CT/ y PET/")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directorio de salida (default: ../resultados_fusion)")
    parser.add_argument("--reset", action="store_true",
                        help="Reiniciar checkpoints")
    args, _ = parser.parse_known_args()

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    pipeline = FusionPipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        reset=args.reset,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
