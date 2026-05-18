"""
Segmentacion de tumores hepaticos desde PET (SUV threshold).

Algoritmo:
  1. Extraer mascara del higado desde la segmentacion de TotalSegmentator
  2. Threshold SUV > 2.5 dentro de la mascara hepatica
  3. Post-procesamiento: remover clusters < 1 cm^3
  4. Crear nodo vtkMRMLSegmentationNode con el resultado

Requiere que TotalSegmentator se haya ejecutado con task="total" (incluye higado).
"""

import logging

logger = logging.getLogger("3DosimTest")

from PipelineOrchestrator.utils import show_progress


def segment_tumor_from_pet(
    pet_node,
    segmentation_node,
    suv_threshold: float = 2.5,
    min_volume_cc: float = 1.0,
    segment_name: str = "liver",
):
    """
    Segmenta tumores desde PET usando SUV threshold dentro de un organo.

    Args:
        pet_node: vtkMRMLScalarVolumeNode del PET (valores SUV)
        segmentation_node: vtkMRMLSegmentationNode de TotalSegmentator
        suv_threshold: valor de SUV para threshold (default 2.5)
        min_volume_cc: volumen minimo en cm^3 para mantener una lesion
        segment_name: nombre del segmento organo en ingles (default "liver", ej: "higado" en TS)

    Returns:
        vtkMRMLSegmentationNode con el(los) tumor(es), o None si no se encuentran.

    Raises:
        RuntimeError: si falla la segmentacion tumoral
    """
    import slicer
    import numpy as np
    from scipy import ndimage as ndi

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  Segmentacion tumoral desde PET (SUV threshold)")
    logger.info("  ========================================================")
    logger.info("")

    show_progress("Segmentando tumor desde PET...")

    # --- 1. Verificar nodos ---
    if pet_node is None:
        raise RuntimeError("Nodo PET no disponible para segmentacion tumoral")
    if segmentation_node is None:
        raise RuntimeError("Nodo de segmentacion no disponible para segmentacion tumoral")

    pet_name = pet_node.GetName()
    logger.info(f"  PET: {pet_name}")
    logger.info(f"  Organo mascara: '{segment_name}'")
    logger.info(f"  SUV threshold: {suv_threshold}")
    logger.info(f"  Volumen minimo lesion: {min_volume_cc} cm^3")

    # --- 2. Extraer mascara del organo desde la segmentacion ---
    logger.info("  Extrayendo mascara del organo...")
    organ_mask = _extract_segment_mask(segmentation_node, segment_name)
    if organ_mask is None:
        raise RuntimeError(
            f"No se encontro el segmento '{segment_name}' en la segmentacion. "
            "TotalSegmentator debe ejecutarse con task='total' para incluir organos."
        )
    organ_voxels = int(np.sum(organ_mask))
    logger.info(f"  Voxeles en '{segment_name}': {organ_voxels}")

    # --- 3. Obtener array PET ---
    logger.info("  Leyendo volumen PET...")
    pet_array = slicer.util.arrayFromVolume(pet_node)  # (K, J, I)
    logger.info(f"  Dimensiones PET: {pet_array.shape}")

    # Verificar que PET y mascara tengan mismas dimensiones
    if pet_array.shape != organ_mask.shape:
        raise RuntimeError(
            f"Dimensiones PET {pet_array.shape} no coinciden con mascara {organ_mask.shape}. "
            "CT y PET deben estar registrados."
        )

    # --- 4. Threshold SUV dentro del organo ---
    logger.info(f"  Aplicando threshold SUV > {suv_threshold}...")
    tumor_mask = np.zeros_like(organ_mask, dtype=np.uint8)
    tumor_region = (pet_array > suv_threshold) & (organ_mask > 0)
    tumor_mask[tumor_region] = 1

    tumor_voxels = int(np.sum(tumor_mask))
    logger.info(f"  Voxeles SUV > {suv_threshold}: {tumor_voxels}")

    if tumor_voxels == 0:
        logger.warning(f"  No se encontraron voxeles con SUV > {suv_threshold}")
        logger.info("  Creando segmentacion tumoral VACIA (sin tumores detectados)")
        # Crear nodo vacio para que el medico pueda segmentar manualmente
        empty_node = _create_tumor_segmentation_node(
            None, pet_node, "Tumor", suv_threshold
        )
        return empty_node

    # --- 5. Post-procesamiento: remover clusters pequenos ---
    logger.info(f"  Filtrando clusters < {min_volume_cc} cm^3...")
    labeled, num_features = ndi.label(tumor_mask)
    if num_features > 0:
        sizes = ndi.sum(tumor_mask, labeled, range(1, num_features + 1))
        spacing = pet_node.GetSpacing()
        voxel_vol_cc = spacing[0] * spacing[1] * spacing[2] / 1000.0
        min_voxels = int(min_volume_cc / voxel_vol_cc)

        kept_voxels = 0
        for i, size in enumerate(sizes, 1):
            if size < min_voxels:
                tumor_mask[labeled == i] = 0
            else:
                kept_voxels += size

        tumor_mask[tumor_mask > 0] = 1
        logger.info(f"  Clusters grandes: {kept_voxels} voxeles")
        logger.info(f"  Clusters pequenos eliminados: {tumor_voxels - kept_voxels} voxeles")

    # --- 6. Volumen tumoral ---
    spacing = pet_node.GetSpacing()
    voxel_vol_cc = spacing[0] * spacing[1] * spacing[2] / 1000.0
    vol_cc = float(np.sum(tumor_mask)) * voxel_vol_cc
    logger.info(f"  Volumen tumoral total: {vol_cc:.1f} cm^3")

    # --- 7. Crear nodo de segmentacion ---
    logger.info("  Creando nodo de segmentacion tumoral...")
    tumor_node = _create_tumor_segmentation_node(
        tumor_mask, pet_node, "Tumor", suv_threshold
    )

    if tumor_node:
        logger.info(f"  Nodo: {tumor_node.GetName()}")
        logger.info("  Segmentacion tumoral completada")
        return tumor_node
    else:
        raise RuntimeError("Fallo al crear nodo de segmentacion tumoral")


def _extract_segment_mask(segmentation_node, segment_name: str):
    """
    Extrae un segmento especifico de un vtkMRMLSegmentationNode como numpy array.

    Args:
        segmentation_node: vtkMRMLSegmentationNode
        segment_name: nombre del segmento a extraer (ej: "higado")

    Returns:
        numpy array 3D uint8 con la mascara, o None si no se encuentra el segmento
    """
    import slicer
    import numpy as np
    from vtk.util import numpy_support
    import vtk

    seg = segmentation_node.GetSegmentation()
    if seg is None:
        return None

    # Buscar segmento por nombre
    segment_ids = vtk.vtkStringArray()
    seg.GetSegmentIDs(segment_ids)

    found_id = None
    for i in range(segment_ids.GetNumberOfValues()):
        sid = segment_ids.GetValue(i)
        segment = seg.GetSegment(sid)
        if segment and segment.GetName().lower() == segment_name.lower():
            found_id = sid
            break

    if found_id is None:
        # Intentar busqueda parcial
        for i in range(segment_ids.GetNumberOfValues()):
            sid = segment_ids.GetValue(i)
            segment = seg.GetSegment(sid)
            if segment and segment_name.lower() in segment.GetName().lower():
                found_id = sid
                logger.info(f"  Segmento encontrado por coincidencia parcial: '{segment.GetName()}'")
                break

    if found_id is None:
        logger.warning(f"  Segmento '{segment_name}' no encontrado en la segmentacion")
        logger.info(f"  Segmentos disponibles:")
        for i in range(segment_ids.GetNumberOfValues()):
            sid = segment_ids.GetValue(i)
            segment = seg.GetSegment(sid)
            if segment:
                logger.info(f"    - {segment.GetName()}")
        return None

    # Exportar SOLO el segmento encontrado a labelmap
    # Usar ExportSegmentToLabelmapNode (singular) que acepta string ID directamente
    labelmap_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLabelMapVolumeNode", "__temp_organ_mask__"
    )

    try:
        # Buscar nodo de referencia para geometria (el CT de la escena)
        ref_node = None
        try:
            ref_node = slicer.util.getNode("3Dosim_CT_anon")
        except Exception:
            pass

        if ref_node is None:
            # Sin referencia, usar directamente (puede fallar si no hay geometria)
            slicer.modules.segmentations.logic().ExportSegmentToLabelmapNode(
                segmentation_node, found_id, labelmap_node
            )
        else:
            slicer.modules.segmentations.logic().ExportSegmentToLabelmapNode(
                segmentation_node, found_id, labelmap_node, ref_node
            )

        image_data = labelmap_node.GetImageData()
        if image_data is None:
            slicer.mrmlScene.RemoveNode(labelmap_node)
            return None

        array = numpy_support.vtk_to_array(image_data)  # (K, J, I)
        mask = (array > 0).astype(np.uint8)

        slicer.mrmlScene.RemoveNode(labelmap_node)
        return mask

    except Exception as e:
        logger.warning(f"  Error exportando segmento: {e}")
        slicer.mrmlScene.RemoveNode(labelmap_node)
        return None


def _create_tumor_segmentation_node(tumor_mask, ref_node, base_name: str, suv_threshold: float):
    """
    Crea un vtkMRMLSegmentationNode desde una mascara numpy.

    Args:
        tumor_mask: numpy array 3D uint8, o None para nodo vacio
        ref_node: nodo de referencia para geometria (ej: PET)
        base_name: nombre base para la segmentacion
        suv_threshold: umbral SUV usado (para el nombre)

    Returns:
        vtkMRMLSegmentationNode
    """
    import slicer
    import numpy as np
    from vtk.util import numpy_support
    import vtk

    # Crear nodo de segmentacion
    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_name = f"Tumor_SUV_{suv_threshold}" if tumor_mask is not None else f"Tumor_VACIO"
    seg_node.SetName(seg_name)
    seg_node.CreateDefaultDisplayNodes()

    if tumor_mask is None or np.sum(tumor_mask) == 0:
        # Nodo vacio — agregar segmento vacio con nombre
        empty_color = [1.0, 0.0, 0.0]  # rojo
        seg_node.GetSegmentation().AddEmptySegment(
            "Tumor", f"Tumor SUV>{suv_threshold}", empty_color
        )
        return seg_node

    # Crear labelmap volume temporal
    label_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLabelMapVolumeNode", "__temp_tumor_label__"
    )

    # Copiar geometria del nodo de referencia
    mat = vtk.vtkMatrix4x4()
    ref_node.GetIJKToRASMatrix(mat)
    label_node.SetIJKToRASMatrix(mat)
    label_node.SetSpacing(ref_node.GetSpacing())
    label_node.SetOrigin(ref_node.GetOrigin())

    # Convertir numpy a vtkImageData
    # tumor_mask es (K, J, I) -> vtk espera (I, J, K)
    tumor_ijk = np.transpose(tumor_mask, (2, 1, 0)).astype(np.uint8)
    flat = tumor_ijk.ravel(order='C')
    vtk_arr = numpy_support.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

    vtk_img = vtk.vtkImageData()
    dims = ref_node.GetImageData().GetDimensions()
    vtk_img.SetDimensions(dims)
    vtk_img.SetSpacing(ref_node.GetSpacing())
    vtk_img.SetOrigin(ref_node.GetOrigin())
    vtk_img.GetPointData().SetScalars(vtk_arr)
    label_node.SetAndObserveImageData(vtk_img)

    # Importar a segmentation
    try:
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            label_node, seg_node
        )
    except Exception as e:
        logger.warning(f"  Fallo import labelmap a segmentation: {e}")
        seg_node.GetSegmentation().AddEmptySegment(
            "Tumor", f"Tumor SUV>{suv_threshold}", [1.0, 0.0, 0.0]
        )

    # Limpiar
    slicer.mrmlScene.RemoveNode(label_node)

    # Renombrar segmento si existe
    seg = seg_node.GetSegmentation().GetSegment("Tumor")
    if seg:
        seg.SetColor(1.0, 0.0, 0.0)

    return seg_node
