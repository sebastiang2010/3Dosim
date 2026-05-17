"""
Paso 1: Convertir segmentacion TS + CT a phantom de tejidos.

Toma el nodo de segmentacion de TotalSegmentator y el CT,
mapea los labels de TS a indices phantom usando TissueConfig,
y produce un array 3D con los tejidos asignados.

Flujo:
  1. Exportar segmentation node a labelmap
  2. Mapear labels TS → indices phantom (TissueConfig.map_ts_to_phantom_label)
  3. Refinar con HU del CT (aire/hueso/tejido blando)
  4. Guardar metadata para pasos siguientes
"""

import logging
import time

logger = logging.getLogger("3DosimTest")


def build_phantom(segmentation_node, ct_node, output_dir: str):
    """
    Convierte la segmentacion de TotalSegmentator en un phantom
    de tejidos 3Dosim usando TissueConfig.

    Args:
        segmentation_node: vtkMRMLSegmentationNode de TotalSegmentator
        ct_node: vtkMRMLScalarVolumeNode del CT (para HU y geometria)
        output_dir: Directorio de salida

    Returns:
        dict con:
            phantom_arr: numpy uint8 array (indices phantom)
            hu_arr: numpy int16 array (HU originales)
            dims: (nx, ny, nz)
            origin: (ox, oy, oz)
            spacing: (sx, sy, sz)
    """
    import numpy as np
    import slicer

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  [PASO 1/5] Phantom desde segmentacion TS")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    # Obtener info del CT
    dims = ct_node.GetImageData().GetDimensions()
    origin = ct_node.GetOrigin()
    spacing = ct_node.GetSpacing()
    logger.info(f"  CT: {dims[0]}x{dims[1]}x{dims[2]}, "
                f"origin={origin[0]:.1f},{origin[1]:.1f},{origin[2]:.1f}, "
                f"spacing={spacing[0]:.3f},{spacing[1]:.3f},{spacing[2]:.3f} mm")

    # 1. Exportar segmentation a labelmap
    logger.info("  Exportando segmentacion a labelmap...")
    labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    labelmap_node.SetName("_ts_labelmap_tmp")

    # Usar Segmentations module logic para exportar
    seg_logic = slicer.modules.segmentations.logic()
    try:
        # ExportAllSegmentsToLabelmapNode(segNode, labelmapNode, referenceVolumeNode)
        seg_logic.ExportAllSegmentsToLabelmapNode(segmentation_node, labelmap_node, ct_node)
    except Exception as e:
        logger.warning(f"  ExportAllSegments fallo: {e}")
        # Fallback: ExportVisibleSegmentsToLabelmapNode
        seg_logic.ExportVisibleSegmentsToLabelmapNode(segmentation_node, labelmap_node, ct_node)

    # Verificar resultado
    label_arr = slicer.util.arrayFromVolume(labelmap_node)  # (K, J, I) numpy
    unique_labels = sorted(set(label_arr.ravel().tolist()))
    logger.info(f"  Labels TS encontrados: {len(unique_labels)}")
    logger.info(f"  Labels: {unique_labels[:20]}{'...' if len(unique_labels) > 20 else ''}")

    # 2. Mapear labels TS → indices phantom
    logger.info("  Mapeando labels TS a indices phantom...")
    from SlicerDosim.SlicerDosimLib import TissueConfig
    config = TissueConfig()

    phantom_arr = np.zeros_like(label_arr, dtype=np.uint8)
    for ts_label in unique_labels:
        if ts_label == 0:
            continue  # fondo
        phantom_idx = config.map_ts_to_phantom_label(int(ts_label))
        mask = label_arr == ts_label
        phantom_arr[mask] = phantom_idx
        if phantom_idx not in (1, 30, 50, 80, 90, 100):
            logger.info(f"    Label TS {ts_label} -> phantom {phantom_idx} (fuera de indices standard)")

    unique_phantom = sorted(set(phantom_arr.ravel().tolist()))
    logger.info(f"  Indices phantom: {unique_phantom}")
    for idx in unique_phantom:
        if idx > 0:
            name = config.get_tissue_name(idx) or "desconocido"
            count = int(np.sum(phantom_arr == idx))
            vol_ml = count * spacing[0] * spacing[1] * spacing[2] / 1000.0
            logger.info(f"    Indice {idx:3d}: {name:20s} -> {count:8d} voxeles ({vol_ml:.1f} mL)")

    # 3. Refinar con HU del CT
    logger.info("  Refinando tejidos con HU del CT...")
    hu_arr = slicer.util.arrayFromVolume(ct_node)
    if hu_arr.shape != phantom_arr.shape:
        logger.warning(f"  Shape mismatch CT {hu_arr.shape} vs phantom {phantom_arr.shape}, usando sin refinar")
    else:
        # Refinar tejido blando (30) en aire (1) o hueso (80) segun HU
        soft_tissue_mask = (phantom_arr == 30)
        if np.any(soft_tissue_mask):
            # Aire: HU < -200 (dentro del cuerpo, como intestinos)
            air_mask = soft_tissue_mask & (hu_arr < -200)
            phantom_arr[air_mask] = 1
            logger.info(f"    Voxeles reclasificados a aire (HU<-200): {int(np.sum(air_mask))}")

            # Hueso: HU > 150 (hueso denso)
            bone_mask = soft_tissue_mask & (hu_arr > 150)
            phantom_arr[bone_mask] = 80
            logger.info(f"    Voxeles reclasificados a hueso (HU>150): {int(np.sum(bone_mask))}")

            # Pulmon: HU entre -900 y -500 (dentro del cuerpo)
            lung_mask = soft_tissue_mask & (hu_arr > -900) & (hu_arr < -500)
            phantom_arr[lung_mask] = 50
            logger.info(f"    Voxeles reclasificados a pulmon (HU -900 a -500): {int(np.sum(lung_mask))}")

    # Limpiar nodo temporal
    slicer.mrmlScene.RemoveNode(labelmap_node)

    elapsed = time.time() - t_start
    logger.info(f"  Phantom generado en {elapsed:.1f}s")
    logger.info(f"  Dimensiones: {phantom_arr.shape}")
    logger.info(f"  Indices finales: {sorted(set(phantom_arr.ravel().tolist()))}")

    # Guardar metadata para pasos siguientes
    phantom_data = {
        "phantom_arr": phantom_arr,
        "hu_arr": hu_arr,
        "dims": dims,
        "origin": origin,
        "spacing": spacing,
    }
    return phantom_data
