"""
Segmentacion simple (threshold + morfologia).

NO usa TotalSegmentator porque el multiprocessing de PyTorch
no funciona en el Python embebido de Slicer.

Flujo:
  1. Threshold: voxels > -200 HU (cuerpo, sin aire)
  2. Cierre morfologico para rellenar huecos
  3. Componente conectada mas grande
  4. Crear segmentacion en Slicer via ImportLabelmapToSegmentationNode
"""

import logging
import os
import time

logger = logging.getLogger("3DosimTest")


def run_segmentation(ct_node, output_dir: str):
    """
    Segmentacion rapida por threshold + morfologia.

    Args:
        ct_node: vtkMRMLScalarVolumeNode del CT
        output_dir: Directorio de salida

    Returns:
        segmentation_node: vtkMRMLSegmentationNode

    Raises:
        RuntimeError: Si algo falla
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
