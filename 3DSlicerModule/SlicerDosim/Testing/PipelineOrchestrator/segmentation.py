"""
Segmentacion con TotalSegmentator (main thread) o simple (threshold + morfologia).

Modos:
  - "totalsegmentator": ejecuta TotalSegmentator en main thread con:
      device="cpu", fast=True, body_seg=True
      MsgBox avisa que Slicer se congelara 5-15 min.
  - "simple": threshold HU > -200 + cierre morfologico + componente conectada.
"""

import logging
import os
import time

logger = logging.getLogger("3DosimTest")


def check_totalsegmentator() -> bool:
    """Verifica si TotalSegmentator esta instalado y funcional."""
    try:
        from totalsegmentator.python_api import totalsegmentator
        logger.info("  TotalSegmentator detectado")
        return True
    except ImportError:
        logger.info("  TotalSegmentator NO disponible")
        logger.info("  -> Instalar: Extension Manager -> TotalSegmentator")
        return False


def run_segmentation_totalsegmentator(ct_node, output_dir: str):
    """
    Ejecuta TotalSegmentator en MAIN thread (NUNCA en thread separado).

    Parametros rapidos: device="cpu", fast=True, body_seg=True.

    IMPORTANTE: TotalSegmentator usa multiprocessing internamente,
    lo cual es incompatible con threading en Slicer embebido.
    Por eso se ejecuta en el main thread y se muestra una advertencia.
    """
    import slicer
    from totalsegmentator.python_api import totalsegmentator

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  TotalSegmentator MODO RAPIDO (main thread)")
    logger.info("  ========================================================")
    logger.info("")

    # Advertencia al usuario
    logger.info("  ATENCION: Slicer se congelara durante 5-15 min mientras")
    logger.info("  TotalSegmentator procesa. No cerrar la ventana.")

    try:
        # Mostrar mensaje en Slicer
        slicer.util.delayDisplay(
            "TotalSegmentator: Slicer se congelara 5-15 min...\n"
            "No cerrar la ventana ni hacer clic.",
            autoClose=False
        )
    except Exception:
        pass

    t_start = time.time()

    # Ruta temporal para NIfTI de salida
    ts_output = os.path.join(output_dir, "totalsegmentator_output")
    os.makedirs(ts_output, exist_ok=True)

    # Ejecutar TotalSegmentator (main thread!)
    logger.info("  Llamando TotalSegmentator (fast, body_seg)...")
    logger.info("  (Slicer no responde hasta terminar)")
    try:
        # totalsegmentator espera el path a un archivo NIfTI
        # Guardar CT temporal como NIfTI
        ct_nifti_path = os.path.join(output_dir, "_ct_temp_for_ts.nii.gz")
        logger.info(f"  Exportando CT a NIfTI temporal: {ct_nifti_path}")
        slicer.util.saveNode(ct_node, ct_nifti_path)

        logger.info("  Ejecutando TotalSegmentator...")
        totalsegmentator(
            input=ct_nifti_path,
            output=ts_output,
            device="cpu",
            fast=True,
            body_seg=True,
        )
        logger.info("  TotalSegmentator completado")

        # Buscar el NIfTI de segmentacion generado
        seg_nifti = None
        for f in os.listdir(ts_output):
            if f.endswith(".nii.gz") or f.endswith(".nii"):
                seg_nifti = os.path.join(ts_output, f)
                break

        if not seg_nifti:
            # Buscar en subdirectorios
            for root, dirs, files in os.walk(ts_output):
                for f in files:
                    if f.endswith(".nii.gz") or f.endswith(".nii"):
                        seg_nifti = os.path.join(root, f)
                        break
                if seg_nifti:
                    break

        if not seg_nifti:
            raise RuntimeError("No se encontro archivo de segmentacion generado por TotalSegmentator")

        logger.info(f"  Segmentacion encontrada: {seg_nifti}")

        # Cargar el NIfTI de segmentacion en Slicer
        seg_node = slicer.util.loadSegmentation(seg_nifti)
        if seg_node is None:
            # Fallback: cargar como volumen label y convertir
            label_node = slicer.util.loadLabelVolume(seg_nifti)
            if label_node is None:
                raise RuntimeError("No se pudo cargar la segmentacion en Slicer")
            seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            seg_node.SetName("TotalSegmentator_Seg")
            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                label_node, seg_node
            )
            slicer.mrmlScene.RemoveNode(label_node)

        seg_node.SetName("TotalSegmentator_Seg")

        # Limpiar temp
        try:
            os.remove(ct_nifti_path)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"  TotalSegmentator FALLO: {e}")
        raise RuntimeError(f"TotalSegmentator fallo: {e}")

    elapsed = int(time.time() - t_start)
    logger.info(f"  TotalSegmentator completado en {elapsed}s")
    logger.info(f"  Nodo: {seg_node.GetName()}")

    # Cerrar dialogo si estaba abierto
    try:
        slicer.util.delayDisplay("", autoClose=True)
    except Exception:
        pass

    return seg_node


def run_segmentation_simple(ct_node, output_dir: str):
    """
    Segmentacion rapida por threshold + morfologia (sin TotalSegmentator).

    Flujo:
      1. Threshold: voxels > -200 HU (cuerpo, sin aire)
      2. Cierre morfologico para rellenar huecos
      3. Componente conectada mas grande
      4. Crear segmentacion en Slicer via ImportLabelmapToSegmentationNode
    """
    import slicer
    import numpy as np
    from scipy import ndimage as ndi

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  Segmentacion SIMPLE (threshold + morfologia)")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    # ---- 1. Obtener array del CT ----
    logger.info("  Leyendo volumen CT...")
    ct_array = slicer.util.arrayFromVolume(ct_node)  # (K, J, I)
    logger.info(f"  Dimensiones CT: {ct_array.shape}")

    # ---- 2. Threshold: cuerpo = HU > -200 ----
    logger.info("  Threshold: HU > -200...")
    body_mask = ct_array > -200

    # ---- 3. Cierre morfologico 3D ----
    logger.info("  Cierre morfologico 3D...")
    struct = ndi.generate_binary_structure(3, 2)
    body_mask = ndi.binary_closing(body_mask, structure=struct, iterations=3)

    # ---- 4. Componente conectada mas grande ----
    logger.info("  Extrayendo componente mas grande...")
    labeled, num_features = ndi.label(body_mask, structure=struct)
    if num_features == 0:
        raise RuntimeError("No se encontro ninguna componente conectada")

    sizes = ndi.sum(body_mask, labeled, range(1, num_features + 1))
    largest = np.argmax(sizes) + 1
    body_mask = (labeled == largest)

    pct = 100 * np.sum(body_mask) / body_mask.size
    logger.info(f"  Voxeles cuerpo: {np.sum(body_mask)} / {body_mask.size} ({pct:.1f}%)")
    logger.info(f"  Mascara generada en {time.time() - t_start:.2f}s")

    # ---- 5. Crear segmentation node ----
    logger.info("  Creando segmentation node en Slicer...")

    # 5a. Crear label map volume desde la mascara
    label_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    label_node.SetName("_body_mask_tmp")

    # Copiar geometria del CT
    import vtk
    mat = vtk.vtkMatrix4x4()
    ct_node.GetIJKToRASMatrix(mat)
    label_node.SetIJKToRASMatrix(mat)
    label_node.SetSpacing(ct_node.GetSpacing())
    label_node.SetOrigin(ct_node.GetOrigin())

    # Convertir numpy a vtkImageData
    import vtk.util.numpy_support as np_support
    label_array = body_mask.astype(np.uint8)  # 0/1
    # vtkImageData espera IJK, numpy da KJI -> reordenar
    label_array_ijk = np.transpose(label_array, (2, 1, 0))  # (I, J, K)
    flat = label_array_ijk.ravel(order='C')
    vtk_arr = np_support.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

    vtk_img = vtk.vtkImageData()
    dims = ct_node.GetImageData().GetDimensions()
    vtk_img.SetDimensions(dims)
    vtk_img.SetSpacing(ct_node.GetSpacing())
    vtk_img.SetOrigin(ct_node.GetOrigin())
    vtk_img.GetPointData().SetScalars(vtk_arr)
    label_node.SetAndObserveImageData(vtk_img)

    logger.info("  Label map creado")

    # 5b. Importar label map a segmentation
    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_node.SetName("Cuerpo_SimpleSeg")

    try:
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            label_node, seg_node
        )
        logger.info("  ImportLabelmapToSegmentationNode OK")
    except Exception as e:
        logger.warning(f"  Fallo import: {e}")
        seg_node.CreateDefaultDisplayNodes()
        # Intentar crear segmento vacio
        seg_node.GetSegmentation().AddEmptySegment(
            "Body", "Cuerpo completo", [0.8, 0.6, 0.2]
        )

    # Limpiar
    slicer.mrmlScene.RemoveNode(label_node)

    seg_node.CreateDefaultDisplayNodes()

    # Renombrar segmento si existe
    seg = seg_node.GetSegmentation().GetSegment("Body")
    if seg:
        seg.SetColor(0.8, 0.6, 0.2)

    elapsed = int(time.time() - t_start)
    logger.info(f"  Segmentacion completada en {elapsed}s")
    logger.info(f"  Nodo: {seg_node.GetName()}")

    return seg_node


def run_segmentation(ct_node, output_dir: str, mode: str = "simple"):
    """
    Punto de entrada unificado.

    Args:
        ct_node: vtkMRMLScalarVolumeNode del CT
        output_dir: Directorio de salida
        mode: "simple" | "totalsegmentator"

    Returns:
        segmentation_node: vtkMRMLSegmentationNode
    """
    if mode == "totalsegmentator":
        if not check_totalsegmentator():
            logger.warning("  TotalSegmentator no instalado, fallback a simple")
            mode = "simple"
        else:
            return run_segmentation_totalsegmentator(ct_node, output_dir)

    # simple por defecto
    return run_segmentation_simple(ct_node, output_dir)


# Mantener compatibilidad
def get_ijk_to_ras_numpy(volume_node):
    import numpy as np
    import vtk
    mat = vtk.vtkMatrix4x4()
    volume_node.GetIJKToRASMatrix(mat)
    m = np.eye(4)
    for i in range(4):
        for j in range(4):
            m[i, j] = mat.GetElement(i, j)
    return m
