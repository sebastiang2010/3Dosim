"""
Crea un tumor sintetico esferico (1 cm radio) en el higado,
y genera higado sano = higado - tumor.

Flujo:
  1. Extraer mascara del higado desde TotalSegmentator
  2. Calcular centroide del higado (coordenadas IJK)
  3. Crear esfera de 1 cm radio en el centroide
  4. Agregar tumor como nuevo segmento (rojo, "Tumor_Sintetico")
  5. Crear "higado_sano" = higado - tumor como nuevo segmento (verde)
"""

import logging
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger("3DosimTest")

from PipelineOrchestrator.utils import show_progress


def add_synthetic_tumor(
    segmentation_node,
    ct_node,
    tumor_radius_mm: float = 10.0,
    liver_segment_name: str = "liver",
) -> dict:
    """
    Anade un tumor esferico sintetico de radio dado en el higado.

    Args:
        segmentation_node: vtkMRMLSegmentationNode con segmentacion TS
        ct_node: vtkMRMLScalarVolumeNode del CT (para geometria)
        tumor_radius_mm: radio del tumor en mm (default 10 mm = 1 cm)
        liver_segment_name: nombre del segmento del higado

    Returns:
        dict con:
            "tumor_center_ijk": (z, y, x) centro del tumor en voxeles
            "tumor_center_ras": (x, y, z) centro en coordenadas RAS
            "tumor_radius_mm": radio del tumor
            "tumor_voxels": cantidad de voxeles del tumor
            "tumor_volume_cc": volumen del tumor en cm^3
            "liver_volume_cc": volumen del higado en cm^3
    """
    import slicer
    import vtk

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  Tumor sintetico: esfera de 1 cm radio en el higado")
    logger.info("  ========================================================")
    logger.info("")

    show_progress("Creando tumor sintetico esferico en el higado...")

    if segmentation_node is None:
        raise RuntimeError("Nodo de segmentacion no disponible")
    if ct_node is None:
        raise RuntimeError("Nodo CT no disponible")

    # --- 1. Extraer mascara del higado ---
    logger.info(f"  Extrayendo '{liver_segment_name}' de la segmentacion...")
    from PipelineOrchestrator.tumor_segmentation import _extract_segment_mask
    liver_mask = _extract_segment_mask(segmentation_node, liver_segment_name)
    if liver_mask is None:
        raise RuntimeError(
            f"No se encontro el segmento '{liver_segment_name}'. "
            "TotalSegmentator debe ejecutarse con task='total'."
        )

    spacing = ct_node.GetSpacing()
    voxel_vol_cc = spacing[0] * spacing[1] * spacing[2] / 1000.0
    liver_voxels = int(np.sum(liver_mask))
    liver_volume_cc = liver_voxels * voxel_vol_cc
    logger.info(f"  Higado: {liver_voxels} voxeles, {liver_volume_cc:.1f} cm^3")

    # --- 2. Calcular centroide del higado ---
    logger.info("  Calculando centroide del higado...")
    centroid = _compute_centroid(liver_mask)
    if centroid is None:
        raise RuntimeError("No se pudo calcular centroide del higado (mascara vacia)")
    cz, cy, cx = centroid
    logger.info(f"  Centroide (IJK):  slice={cz}, row={cy}, col={cx}")
    logger.info(f"  Centroide (RAS):  "
                f"{cx * spacing[0]:.1f}, {cy * spacing[1]:.1f}, {cz * spacing[2]:.1f} mm")

    # Verificar que el centroide este dentro del higado
    if liver_mask[cz, cy, cx] == 0:
        logger.warning("  Centroide en voxel NO higado. Buscando voxel mas cercano...")
        centroid = _find_nearest_liver_voxel(liver_mask, cz, cy, cx)
        cz, cy, cx = centroid
        logger.info(f"  Centroide corregido (IJK): slice={cz}, row={cy}, col={cx}")

    # --- 3. Crear mascara esferica de 1 cm radio ---
    logger.info(f"  Creando esfera de {tumor_radius_mm} mm radio...")
    tumor_mask = _create_sphere_mask(
        liver_mask.shape, cz, cy, cx,
        tumor_radius_mm, spacing
    )

    # Intersectar con el higado (el tumor solo crece dentro del higado)
    tumor_mask = tumor_mask & (liver_mask > 0)

    tumor_voxels = int(np.sum(tumor_mask))
    tumor_volume_cc = tumor_voxels * voxel_vol_cc
    logger.info(f"  Tumor: {tumor_voxels} voxeles, {tumor_volume_cc:.2f} cm^3")

    if tumor_voxels == 0:
        raise RuntimeError(
            "El tumor sintetico tiene 0 voxeles dentro del higado. "
            "Revise que el radio sea suficiente y el higado sea visible."
        )

    # --- 4. Agregar tumor como segmento ---
    logger.info("  Agregando tumor a la segmentacion...")
    _add_mask_as_segment(
        segmentation_node, ct_node, tumor_mask,
        segment_name="Tumor_Sintetico",
        color=[1.0, 0.0, 0.0],  # Rojo
    )

    # --- 5. Crear higado sano = higado - tumor ---
    logger.info("  Creando higado sano = higado - tumor...")
    healthy_mask = (liver_mask > 0) & (~tumor_mask)
    healthy_voxels = int(np.sum(healthy_mask))
    healthy_volume_cc = healthy_voxels * voxel_vol_cc
    logger.info(f"  Higado sano: {healthy_voxels} voxeles, {healthy_volume_cc:.1f} cm^3")

    _add_mask_as_segment(
        segmentation_node, ct_node, healthy_mask.astype(np.uint8),
        segment_name="higado_sano",
        color=[0.0, 1.0, 0.0],  # Verde
    )

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  Tumor sintetico creado exitosamente")
    logger.info(f"    Radio:       {tumor_radius_mm} mm")
    logger.info(f"    Volumen:     {tumor_volume_cc:.2f} cm^3")
    logger.info(f"    Centro IJK:  ({cz}, {cy}, {cx})")
    logger.info(f"    Higado sano: {healthy_volume_cc:.1f} cm^3")
    logger.info("  ========================================================")
    logger.info("")

    show_progress("Tumor sintetico + higado sano creados OK")

    return {
        "tumor_center_ijk": (int(cz), int(cy), int(cx)),
        "tumor_radius_mm": tumor_radius_mm,
        "tumor_voxels": int(tumor_voxels),
        "tumor_volume_cc": round(tumor_volume_cc, 2),
        "liver_volume_cc": round(liver_volume_cc, 1),
        "healthy_liver_volume_cc": round(healthy_volume_cc, 1),
    }


def _compute_centroid(mask: np.ndarray) -> Optional[Tuple[int, int, int]]:
    """Calcula el centroide de una mascara binaria 3D."""
    coords = np.argwhere(mask > 0)
    if coords.size == 0:
        return None
    centroid = coords.mean(axis=0).astype(int)
    return (centroid[0], centroid[1], centroid[2])


def _find_nearest_liver_voxel(
    mask: np.ndarray, z: int, y: int, x: int
) -> Tuple[int, int, int]:
    """Busca el voxel de higado mas cercano al punto (z, y, x)."""
    liver_coords = np.argwhere(mask > 0)
    if liver_coords.size == 0:
        raise RuntimeError("No hay voxeles de higado en la mascara")
    target = np.array([z, y, x])
    dists = np.sum((liver_coords - target) ** 2, axis=1)
    nearest = liver_coords[np.argmin(dists)]
    return (nearest[0], nearest[1], nearest[2])


def _create_sphere_mask(
    shape: Tuple[int, int, int],
    cz: int, cy: int, cx: int,
    radius_mm: float,
    spacing: Tuple[float, float, float],
) -> np.ndarray:
    """
    Crea una mascara binaria esferica 3D.

    Args:
        shape: (K, J, I) dimensiones del volumen
        cz, cy, cx: centro en coordenadas IJK (z=slice, y=row, x=col)
        radius_mm: radio en mm
        spacing: (sx, sy, sz) espaciado en mm

    Returns:
        numpy array uint8 con 1 en la esfera
    """
    sz, sy, sx = spacing
    Z, Y, X = np.ogrid[:shape[0], :shape[1], :shape[2]]
    # Distancia euclidiana en mm desde el centro
    dist_mm = np.sqrt(
        ((Z - cz) * sz) ** 2 +
        ((Y - cy) * sy) ** 2 +
        ((X - cx) * sx) ** 2
    )
    mask = (dist_mm <= radius_mm).astype(np.uint8)
    return mask


def _add_mask_as_segment(
    segmentation_node,
    ref_volume_node,
    mask: np.ndarray,
    segment_name: str = "Tumor",
    color: list = None,
):
    """
    Convierte una mascara numpy 3D a un segmento en el nodo de segmentacion.

    Args:
        segmentation_node: vtkMRMLSegmentationNode destino
        ref_volume_node: volumen de referencia (para geometria IJK->RAS)
        mask: numpy array 3D uint8 con la mascara
        segment_name: nombre del nuevo segmento
        color: [R, G, B] color del segmento (default [1,0,0])
    """
    import slicer
    import vtk

    if color is None:
        color = [1.0, 0.0, 0.0]

    # Crear labelmap temporal con la mascara
    labelmap_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLabelMapVolumeNode", f"__temp_{segment_name}__"
    )
    labelmap_node.SetOrigin(ref_volume_node.GetOrigin())
    labelmap_node.SetSpacing(ref_volume_node.GetSpacing())
    ijk_to_ras = vtk.vtkMatrix4x4()
    ref_volume_node.GetIJKToRASMatrix(ijk_to_ras)
    labelmap_node.SetIJKToRASMatrix(ijk_to_ras)

    # Copiar la mascara al labelmap
    arr = np.zeros(mask.shape, dtype=np.int16)
    arr[mask > 0] = 1
    slicer.util.updateVolumeFromArray(labelmap_node, arr)

    # Renombrar labelmap temporal para que el segmento herede el nombre
    labelmap_node.SetName(f"__import_{segment_name}__")

    # Importar labelmap a segmentacion usando API de Slicer
    # Esto crea un nuevo segmento con label value 1
    num_segs_before = segmentation_node.GetSegmentation().GetNumberOfSegments()
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
        labelmap_node, segmentation_node
    )
    num_segs_after = segmentation_node.GetSegmentation().GetNumberOfSegments()

    # Buscar el nuevo segmento creado y renombrarlo
    if num_segs_after > num_segs_before:
        seg_ids = vtk.vtkStringArray()
        segmentation_node.GetSegmentation().GetSegmentIDs(seg_ids)
        for i in range(seg_ids.GetNumberOfValues()):
            sid = seg_ids.GetValue(i)
            seg = segmentation_node.GetSegmentation().GetSegment(sid)
            if seg and seg.GetName().startswith("__import_"):
                seg.SetName(segment_name)
                seg.SetColor(color)
                break

    slicer.mrmlScene.RemoveNode(labelmap_node)

    logger.info(f"  Segmento '{segment_name}' agregado con {int(np.sum(mask))} voxeles")
