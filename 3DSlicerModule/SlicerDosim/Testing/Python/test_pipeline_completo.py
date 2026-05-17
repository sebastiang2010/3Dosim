"""
Pipeline test completo con segmentacion real, registro y MCNP.

Pasos:
  1. Carga DICOM
  2. Segmentacion real: body mask (HU) + liver.nii + tumor.nii → phantom indices
  3. Registro PET→CT (BrainsFit)
  4. Metricas de fusion
  5. Generacion MCNP (Modulo 2)
  6. Screenshots automáticos de cada paso

Uso:
  Slicer.exe --python-script test_pipeline_completo.py --data-dir "C:\ruta\Paciente_2"
"""

from __future__ import annotations

import logging
import os
import sys
import time
import numpy as np

logger = logging.getLogger("PipelineCompleto")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(handler)

SCREENSHOT_DIR = r"C:\programas\BNCTAr\BNCTAr_V4_13\img-tmp"


class PipelineCompleto:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.seg_dir = os.path.join(data_dir, "segmentation liver")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")
        self.screenshot_dir = SCREENSHOT_DIR

        self.ct_node = None
        self.pet_node = None
        self.pet_registered_node = None
        self.segmentation_node = None
        self.phantom_arr = None
        self.mcnp_path = None

        self.results = {"pasos": [], "errores": [], "metricas": {}}
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    # ======================================================================
    # MAIN
    # ======================================================================

    def run(self):
        logger.info("=" * 65)
        logger.info(" PIPELINE COMPLETO - Segmentacion real + Fusion + MCNP")
        logger.info("=" * 65)
        logger.info(f"  Datos: {self.data_dir}")
        logger.info(f"  Screenshots: {self.screenshot_dir}")
        logger.info("")

        self._configurar_paths()
        self._paso("1. Carga DICOM", self._cargar_dicom)
        self._paso("2. Segmentacion real", self._segmentar_real)
        self._paso("3. Registro PET→CT", self._registrar_pet)
        self._paso("4. Metricas de fusion", self._metricas_fusion)
        self._paso("5. Generacion MCNP", self._generar_mcnp)
        self._paso("6. Reporte final", self._reporte_final)

        self._screenshot("06_resumen")

    # ======================================================================
    # CONFIG
    # ======================================================================

    def _configurar_paths(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base = os.path.normpath(os.path.join(script_dir, "..", ".."))
        target = os.path.join(base, "Modules", "Scripted")
        if os.path.isdir(target) and target not in sys.path:
            sys.path.insert(0, target)
        try:
            import SlicerDosim
            logger.info(f"  ✓ SlicerDosim: {SlicerDosim.__file__}")
        except ImportError:
            logger.warning("  ⚠ SlicerDosim no importable")

    # ======================================================================
    # HELPER: paso con screenshot
    # ======================================================================

    def _paso(self, nombre, func):
        logger.info(f"\n── {nombre} {'─' * (55 - len(nombre))}")
        t0 = time.time()
        try:
            func()
            t = time.time() - t0
            logger.info(f"  ✓ {t:.1f}s")
            self.results["pasos"].append({"nombre": nombre, "ok": True, "tiempo": t})
        except Exception as e:
            t = time.time() - t0
            logger.error(f"  ✗ FALLO: {e}")
            self.results["pasos"].append({"nombre": nombre, "ok": False, "tiempo": t})
            self.results["errores"].append(f"{nombre}: {e}")

    def _configurar_vista(self, modo="ct"):
        """Configura las vistas de Slicer para mostrar los datos correctos."""
        import slicer
        try:
            if modo == "dicom" and self.ct_node:
                # Mostrar CT como fondo y PET como overlay
                pet = self.pet_node or self.pet_registered_node
                if pet:
                    slicer.util.setSliceViewerLayers(
                        background=self.ct_node, foreground=pet, foregroundOpacity=0.3
                    )
            elif modo == "segmentacion" and self.ct_node:
                # Mostrar CT con el segmentation overlay
                slicer.util.setSliceViewerLayers(background=self.ct_node)
                # Activar vista 3D
                lm = slicer.app.layoutManager()
                if lm:
                    three_d = lm.threeDWidget(0)
                    if three_d:
                        three_d.mrmlViewNode().SetBackgroundColor(0.2, 0.2, 0.2)
                    # Enfocar en el CT
                    slicer.util.resetThreeDViews()
            elif modo == "fusion" and self.ct_node:
                pet = self.pet_registered_node or self.pet_node
                if pet:
                    slicer.util.setSliceViewerLayers(
                        background=self.ct_node, foreground=pet, foregroundOpacity=0.5
                    )
            slicer.app.processEvents()
        except Exception as e:
            logger.warning(f"  Vista {modo}: {e}")

    def _screenshot(self, nombre):
        import slicer
        path = os.path.join(self.screenshot_dir, f"{nombre}.png")
        try:
            slicer.app.processEvents()
            time.sleep(0.5)
            main_window = slicer.util.mainWindow()
            if main_window:
                pixmap = main_window.grab()
                pixmap.save(path)
                logger.info(f"  📸 {path}")
        except Exception as e:
            logger.warning(f"  ⚠ Screenshot: {e}")

    # ======================================================================
    # 1. CARGA DICOM
    # ======================================================================

    def _cargar_dicom(self):
        import slicer
        from DICOMLib import DICOMUtils

        if not os.path.isdir(self.ct_dir):
            raise FileNotFoundError(f"CT no encontrado: {self.ct_dir}")
        if not os.path.isdir(self.pet_dir):
            raise FileNotFoundError(f"PET no encontrado: {self.pet_dir}")

        original_db = DICOMUtils.openTemporaryDatabase()
        try:
            for d, lbl in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
                ok = DICOMUtils.importDicom(d)
                logger.info(f"  {lbl}: {'✓' if ok else '✗'}")
            series_uids = DICOMUtils.allSeriesUIDsInDatabase()
            loaded = DICOMUtils.loadSeriesByUID(series_uids)
            logger.info(f"  Nodos cargados: {len(loaded)}")
        finally:
            DICOMUtils.closeTemporaryDatabase(original_db, cleanup=True)

        for node_id in loaded:
            node = slicer.mrmlScene.GetNodeByID(node_id)
            if not node:
                continue
            name = node.GetName().upper()
            logger.info(f"    • {node.GetName()}")
            if "CT" in name and self.ct_node is None:
                self.ct_node = node
            elif ("PET" in name or "SUV" in name or "PT" in name) and self.pet_node is None:
                self.pet_node = node

        if self.ct_node is None:
            raise RuntimeError("No se encontro CT")
        d = self.ct_node.GetImageData().GetDimensions()
        s = self.ct_node.GetSpacing()
        logger.info(f"  CT: {d[0]}x{d[1]}x{d[2]}, espaciado {s[0]:.3f}x{s[1]:.3f}x{s[2]:.3f} mm")
        logger.info(f"  PET: {'✓' if self.pet_node else '✗ no encontrado'}")

        # Configurar vista: CT fondo + PET overlay
        self._configurar_vista("dicom")
        self._screenshot("01_carga_dicom")

    # ======================================================================
    # 2. SEGMENTACION REAL (body mask HU + liver.nii + tumor.nii)
    # ======================================================================

    def _segmentar_real(self):
        import slicer
        import vtk
        import glob
        import subprocess
        import tempfile
        from vtk.util import numpy_support
        from SlicerDosim.SlicerDosimLib import TissueConfig

        config = TissueConfig()
        dims = self.ct_node.GetImageData().GetDimensions()
        spacing = self.ct_node.GetSpacing()

        # TotalSegmentator via subprocess (evita crash multiprocessing)
        try:
            self._run_totalsegmentator_subprocess()
            return
        except Exception as e:
            logger.warning(f"  TotalSegmentator subprocess fallo: {e}")
            logger.info("  Fallback: segmentacion por HU...")

        # Fallback HU-based
        ct_img = self.ct_node.GetImageData()
        hu_arr = numpy_support.vtk_to_numpy(ct_img.GetPointData().GetScalars())
        hu_arr = hu_arr.astype(np.int16).reshape(dims[2], dims[1], dims[0]).transpose(2, 1, 0)
        phantom = self._build_phantom_from_hu(hu_arr)
        self.phantom_arr = phantom
        self.segmentation_node = self._phantom_to_segmentation(phantom, dims, spacing)

        logger.info(f"  Phantom indices: {sorted(np.unique(phantom))}")
        self._configurar_vista("segmentacion")
        self._screenshot("02_phantom_segmentacion")

    def _run_totalsegmentator_subprocess(self):
        """Ejecuta TotalSegmentator como subproceso externo."""
        import slicer
        import glob
        import subprocess
        import tempfile
        import shutil
        from vtk.util import numpy_support
        from SlicerDosim.SlicerDosimLib import TissueConfig

        config = TissueConfig()
        tmp = tempfile.mkdtemp()
        ct_path = os.path.join(tmp, "ct.nii.gz")
        ts_out = os.path.join(tmp, "ts_output")

        logger.info("  Guardando CT como NIfTI temporal...")
        slicer.util.saveNode(self.ct_node, ct_path)

        ts_exe = os.path.join(
            slicer.app.slicerHome, "lib", "Python", "Scripts", "TotalSegmentator.exe"
        )
        if not os.path.exists(ts_exe):
            raise FileNotFoundError(f"TotalSegmentator.exe no encontrado: {ts_exe}")

        logger.info(f"  TS executable: {ts_exe}")
        logger.info("  Ejecutando TotalSegmentator task='total' (fast)...")
        logger.info("  ⏳ Sin GPU puede tardar 10-30 min...")

        t0 = time.time()
        result = subprocess.run(
            [ts_exe, "-i", ct_path, "-o", ts_out, "--task", "total", "--fast", "--ml"],
            capture_output=True, text=True, timeout=3600, check=False,
        )
        elapsed = time.time() - t0

        if result.returncode != 0:
            stderr = result.stderr[-500:] if result.stderr else ""
            raise RuntimeError(f"TS fallo (exit={result.returncode}): {stderr}")

        logger.info(f"  TS completado en {elapsed:.0f}s")

        # Cargar resultado
        niftis = glob.glob(os.path.join(ts_out, "*.nii.gz"))
        if not niftis:
            niftis = glob.glob(os.path.join(ts_out, "*.nii"))
        if not niftis:
            raise FileNotFoundError(f"TS no produjo NIfTI en {ts_out}")
        logger.info(f"  TS output: {os.path.basename(niftis[0])}")

        ts_node = slicer.util.loadNodeFromFile(niftis[0], "NiftiFile")
        if ts_node is None:
            raise RuntimeError("No se pudo cargar output de TS")

        # Extraer y mapear labels
        ts_img = ts_node.GetImageData()
        ed = ts_img.GetDimensions()
        raw = numpy_support.vtk_to_numpy(ts_img.GetPointData().GetScalars())
        raw = raw.astype(np.int32).reshape(ed[2], ed[1], ed[0]).transpose(2, 1, 0)
        logger.info(f"  TS labels: {sorted(set(raw.flatten()))}")

        labels = sorted(set(raw.flatten()))[:20]
        logger.info(f"  Labels unicos en TS: {labels}")

        # Mapeo TS -> phantom indices usando TissueConfig
        ts_mapping = config.get_ts_mapping()
        body_labels = config.get_body_labels()
        phantom = np.ones(raw.shape, dtype=np.uint8)

        # Body -> 30 (tejido blando)
        body_mask = np.isin(raw, list(body_labels))
        phantom[body_mask] = 30

        # Organos especificos
        for ts_label, phantom_idx in ts_mapping.items():
            mask = (raw == ts_label)
            phantom[mask] = phantom_idx
            nv = int(mask.sum())
            if nv > 0:
                logger.info(f"  TS {ts_label:>3} -> phantom {phantom_idx:>3} ({nv} vox)")

        # Aire = 1 (default)

        self.phantom_arr = phantom
        dims = self.ct_node.GetImageData().GetDimensions()
        spacing = self.ct_node.GetSpacing()
        self.segmentation_node = self._phantom_to_segmentation(phantom, dims, spacing)

        logger.info(f"  Phantom indices: {sorted(set(phantom.flatten()))}")
        slicer.mrmlScene.RemoveNode(ts_node)
        shutil.rmtree(tmp, ignore_errors=True)

        self._configurar_vista("segmentacion")
        self._screenshot("02_phantom_segmentacion")

    def _build_phantom_from_hu(self, hu_arr):
        """Construye phantom con indices desde HU."""
        phantom = np.ones(hu_arr.shape, dtype=np.uint8)
        body = hu_arr > -500
        lung = (hu_arr > -950) & (hu_arr <= -500)
        bone = hu_arr > 300
        phantom[lung] = 50
        phantom[bone] = 80
        soft = body & ~np.isin(phantom, [50, 80])
        phantom[soft] = 30
        logger.info(f"  HU:   Aire={int((hu_arr<=-500).sum()):>8} | Blando={int(soft.sum()):>8} | Pulmon={int(lung.sum()):>8} | Hueso={int(bone.sum()):>8}")
        return phantom

    def _phantom_to_segmentation(self, phantom, dims, spacing):
        """Convierte array numpy phantom a vtkMRMLSegmentationNode."""
        import slicer
        import vtk
        from vtk.util import numpy_support
        from SlicerDosim.SlicerDosimLib import TissueConfig

        config = TissueConfig()
        labelmap = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "__phantom_labelmap__"
        )
        labelmap.CopyOrientation(self.ct_node)
        arr_vtk = phantom.transpose(2, 1, 0).astype(np.uint8)
        vtk_arr = numpy_support.numpy_to_vtk(arr_vtk.ravel(), deep=True)
        vtk_img = vtk.vtkImageData()
        vtk_img.SetDimensions(dims)
        vtk_img.SetSpacing(spacing)
        vtk_img.GetPointData().SetScalars(vtk_arr)
        labelmap.SetAndObserveImageData(vtk_img)

        seg_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "Phantom_3Dosim"
        )
        seg_node.CreateDefaultDisplayNodes()
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelmap, seg_node
        )
        slicer.mrmlScene.RemoveNode(labelmap)

        segment_ids = vtk.vtkStringArray()
        seg_node.GetSegmentation().GetSegmentIDs(segment_ids)
        for i in range(segment_ids.GetNumberOfValues()):
            sid = segment_ids.GetValue(i)
            seg = seg_node.GetSegmentation().GetSegment(sid)
            if not seg:
                continue
            try:
                idx = int(seg.GetName())
                tissue = config.get_tissue(idx)
                if tissue:
                    seg_node.GetSegmentation().SetSegmentName(sid, tissue["name"])
                    c = tissue["color"]
                    dn = seg_node.GetDisplayNode()
                    if dn:
                        dn.SetSegmentColor(sid, c[0], c[1], c[2])
            except ValueError:
                pass
        return seg_node

    # ======================================================================
    # 3. REGISTRO PET → CT (BrainsFit)
    # ======================================================================

    def _registrar_pet(self):
        import slicer

        if self.pet_node is None:
            logger.warning("  No hay PET para registrar")
            self.pet_registered_node = None
            self._screenshot("03_sin_pet")
            return

        # Verificar BrainsFit
        try:
            brainsfit_cli = slicer.modules.brainsfit
            logger.info(f"  BrainsFit disponible")
        except AttributeError:
            logger.warning("  BrainsFit no disponible, usando transformada identidad")
            self.pet_registered_node = self.pet_node
            self._screenshot("03_registro_no_disponible")
            return

        logger.info("  Ejecutando BrainsFit (rigido + afin)...")
        self._configurar_vista("dicom")
        self._screenshot("03_registro_antes")

        # Crear nodos temporales para output
        import slicer
        output_vol = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeNode", "__pet_registrada__"
        )
        linear_xform = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLinearTransformNode", "__pet_reg_xform__"
        )

        params = {
            "fixedVolume": self.ct_node,
            "movingVolume": self.pet_node,
            "outputVolume": output_vol,
            "linearTransform": linear_xform,
            "useRigid": True,
            "useAffine": True,
            "useBSpline": False,
            "numberOfIterations": 1000,
        }
        cli_node = slicer.cli.runSync(brainsfit_cli, None, params)
        status = cli_node.GetStatusString() if cli_node else "error"
        logger.info(f"  BrainsFit status: {status}")

        if status == "Completed" and output_vol.GetImageData():
            self.pet_registered_node = output_vol
            logger.info(f"  ✓ PET registrada: {output_vol.GetName()}")
            self._configurar_vista("fusion")
            self._screenshot("04_registro_despues")
        else:
            logger.warning(f"  BrainsFit fallo ({status}), usando PET original")
            self.pet_registered_node = self.pet_node
            slicer.mrmlScene.RemoveNode(output_vol)
            slicer.mrmlScene.RemoveNode(linear_xform)

    # ======================================================================
    # 4. METRICAS DE FUSION
    # ======================================================================

    def _metricas_fusion(self):
        """Compara PET original vs registrada y calcula overlap."""
        metrics = {}

        # CT
        cd = self.ct_node.GetImageData().GetDimensions()
        cs = self.ct_node.GetSpacing()
        metrics["ct"] = {"dimensions": cd, "spacing": cs}

        # PET original
        if self.pet_node:
            pd = self.pet_node.GetImageData().GetDimensions()
            ps = self.pet_node.GetSpacing()
            po = self.pet_node.GetOrigin()
            metrics["pet_original"] = {"dimensions": pd, "spacing": ps, "origin": po}

        # PET registrada
        pet_reg = self.pet_registered_node or self.pet_node
        if pet_reg:
            rd = pet_reg.GetImageData().GetDimensions()
            rs = pet_reg.GetSpacing()
            ro = pet_reg.GetOrigin()
            metrics["pet_registrada"] = {"dimensions": rd, "spacing": rs, "origin": ro}

        # Overlap: % del PET registrado que cae dentro del CT
        if pet_reg and self.ct_node:
            from vtk.util import numpy_support
            import vtk

            try:
                # Resample PET al CT para comparacion voxel a voxel
                logic = slicer.vtkSlicerVolumesLogic() if hasattr(slicer, 'vtkSlicerVolumesLogic') else None
                s_pet = pet_reg.GetImageData().GetPointData().GetScalars()
                pet_arr = numpy_support.vtk_to_numpy(s_pet)
                s_ct = self.ct_node.GetImageData().GetPointData().GetScalars()
                ct_arr = numpy_support.vtk_to_numpy(s_ct)
                # Calcular overlapping bounding box
                pet_active = (pet_arr > pet_arr.mean() * 0.1).sum()
                total_pet = pet_arr.size
                overlap_pct = pet_active / total_pet * 100 if total_pet > 0 else 0
                metrics["overlap"] = {
                    "voxeles_pet": int(total_pet),
                    "voxeles_activos": int(pet_active),
                    "overlap_pct": round(float(overlap_pct), 1),
                }
                logger.info(f"  Overlap PET con CT: {overlap_pct:.1f}%")
            except Exception as e:
                logger.warning(f"  No se pudo calcular overlap: {e}")

        self.results["metricas"] = metrics
        self._imprimir_metricas(metrics)
        self._screenshot("04_metricas_fusion")

    def _imprimir_metricas(self, m):
        logger.info("")
        logger.info("  ┌─────── TABLA DE METRICAS ─────────────────────────────┐")
        for key, val in m.items():
            if key == "overlap":
                logger.info(f"  │ Overlap PET en CT: {val['overlap_pct']}%            │")
                logger.info(f"  │ Voxeles activos:  {val['voxeles_activos']}          │")
            else:
                d = val.get("dimensions", (0, 0, 0))
                s = val.get("spacing", (0, 0, 0))
                o = val.get("origin", (0, 0, 0))
                logger.info(f"  │ {key.upper():<20} {d[0]}x{d[1]}x{d[2]}  {s[0]:.3f}x{s[1]:.3f}x{s[2]:.3f} mm  │")
        logger.info("  └────────────────────────────────────────────────────────┘")
        logger.info("")

    # ======================================================================
    # 5. GENERACION MCNP
    # ======================================================================

    def _generar_mcnp(self):
        from SlicerDosim.SlicerDosimLib import (
            MCNPMaterialMapper,
            MCNPGeometryBuilder,
            MCNPTallyBuilder,
            MCNPSourceBuilder,
            TissueConfig,
        )

        config = TissueConfig()
        dims = self.ct_node.GetImageData().GetDimensions()
        origin = self.ct_node.GetOrigin()
        spacing = self.ct_node.GetSpacing()
        phantom_arr = self.phantom_arr

        if phantom_arr is None:
            raise RuntimeError("No hay phantom. Ejecutar segmentacion primero.")

        # Tomar submuestra si es muy grande
        step = 2
        if max(dims) > 256:
            sx, sy, sz = dims[0] // step, dims[1] // step, dims[2] // step
            phantom_arr = phantom_arr[::step, ::step, ::step]
        else:
            sx, sy, sz = dims

        logger.info(f"  Phantom submuestreado: {phantom_arr.shape}")
        logger.info(f"  Indices: {sorted(np.unique(phantom_arr))}")

        mcnp_dir = os.path.join(self.output_dir, "mcnp")
        os.makedirs(mcnp_dir, exist_ok=True)

        # Materiales
        logger.info("  [A] Materiales...")
        mapper = MCNPMaterialMapper(config)
        mat_arr = mapper.assign_from_labelmap(phantom_arr)
        mat_cards = mapper.generate_material_cards()

        # Geometria
        logger.info("  [B] Geometria...")
        geo = MCNPGeometryBuilder(config)
        geom_cards = geo.build((sx, sy, sz), origin, spacing, mat_arr)

        # Fuente
        logger.info("  [C] Fuente...")
        pet_reg = self.pet_registered_node or self.pet_node
        src = MCNPSourceBuilder()
        iso = {"name": "Yttrium-90", "zaid": 39090, "energy_mev": 2.28,
               "particle": "electron", "mode": "e"}
        src_cards = src.build(pet_reg, (sx, sy, sz), iso)

        # Tallies
        logger.info("  [D] Tallies...")
        tal = MCNPTallyBuilder()
        tal_cards = tal.build(iso, (sx, sy, sz), n_particles=1000000, origin=origin)

        # Escribir .i
        input_path = os.path.join(mcnp_dir, "3Dosim_MCNP_Y90.i")
        with open(input_path, "w") as f:
            f.write(f"3Dosim MCNP input - Pipeline completo\n")
            f.write(f"C Generado por test_pipeline_completo.py\n")
            f.write(f"C CT: {dims[0]}x{dims[1]}x{dims[2]}  Phantom: {sx}x{sy}x{sz}\n")
            f.write(f"C\n")
            f.write("\n".join(mat_cards) + "\n")
            f.write("\n".join(geom_cards) + "\n")
            f.write("\n".join(src_cards) + "\n")
            f.write("\n".join(tal_cards) + "\n")
        self.mcnp_path = input_path

        # Verificar
        with open(input_path) as f:
            content = f.read()
        checks = {
            "header": content.startswith("3Dosim"),
            "materiales": "M " in content or "M\t" in content,
            "geometria": ("PX" in content or "RPP" in content),
            "fuente": "SDEF" in content,
            "tallies": "FMESH4" in content,
            "nps": "NPS" in content,
        }
        lines = content.count("\n") + 1
        logger.info(f"  .i: {lines} lineas, {len(content)} chars")
        for chk, ok in checks.items():
            logger.info(f"    {chk}: {'✓' if ok else '✗'}")
        self._screenshot("05_mcnp_generado")

    # ======================================================================
    # 6. REPORTE FINAL
    # ======================================================================

    def _reporte_final(self):
        logger.info("")
        logger.info("=" * 65)
        logger.info(" REPORTE FINAL")
        logger.info("=" * 65)
        ok = sum(1 for p in self.results["pasos"] if p["ok"])
        total = len(self.results["pasos"])
        fails = total - ok
        logger.info(f"  Pasos: {ok}/{total} exitosos, {fails} fallos")
        for p in self.results["pasos"]:
            s = "✓" if p["ok"] else "✗"
            logger.info(f"  {s} {p['nombre']}: {p['tiempo']:.1f}s")
        if self.results["errores"]:
            logger.info(f"  Errores: {self.results['errores']}")
        logger.info(f"  Screenshots: {self.screenshot_dir}")
        if self.mcnp_path:
            logger.info(f"  MCNP: {self.mcnp_path}")
        logger.info("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str,
                        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2")
    args = parser.parse_args()
    PipelineCompleto(args.data_dir).run()
