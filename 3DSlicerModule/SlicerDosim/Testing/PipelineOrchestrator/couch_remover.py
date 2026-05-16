"""
Eliminacion de camilla (mesa de exploracion) y aire exterior del CT.

Algoritmo:
  1. Threshold CT > -200 HU para crear mascara corporal
  2. Cierre morfologico (dilate + erode) para rellenar huecos
  3. Componente conectada mas grande -> cuerpo del paciente
  4. En cada corte axial, identificar y eliminar la camilla
     (estructura horizontal que toca el borde inferior del FOV)
  5. Aplicar mascara refinada al volumen
"""

import logging

logger = logging.getLogger("3DosimTest")


def remove_couch_and_air(ct_node):
    """
    Elimina la camilla y el aire exterior del volumen CT.

    Args:
        ct_node: vtkMRMLScalarVolumeNode del CT
                 (se modifica in-place: los voxeles fuera del cuerpo se setean a -1024 HU)
    """
    import numpy as np
    from vtk.util import numpy_support
    import vtk
    from .utils import show_progress

    logger.info("  Eliminando camilla y aire del volumen CT...")
    show_progress("Eliminando camilla y aire...")

    ct_img = ct_node.GetImageData()
    dims = ct_img.GetDimensions()

    # Extraer array CT como numpy
    ct_array_vtk = ct_img.GetPointData().GetScalars()
    ct_np = numpy_support.vtk_to_numpy(ct_array_vtk).reshape(dims[2], dims[1], dims[0])

    logger.info(f"  CT array: {dims[0]}x{dims[1]}x{dims[2]}")

    # Paso 1: Threshold para mascara corporal (HU > -200)
    body_mask = (ct_np > -200).astype(np.uint8)

    # Paso 2: Rellenar huecos con cierre morfologico 3D
    show_progress("Aplicando cierre morfologico...")
    try:
        from scipy.ndimage import binary_closing
        struct = np.ones((3, 3, 3), dtype=bool)
        body_mask = binary_closing(body_mask, structure=struct, iterations=3).astype(np.uint8)
        scipy_available = True
    except ImportError:
        logger.info("  scipy no disponible, usando morfologia simple")
        scipy_available = False

    # Paso 3: Encontrar componente conectada mas grande (el paciente)
    show_progress("Identificando cuerpo del paciente...")
    z_range = np.where(body_mask.sum(axis=(1, 2)) > 0)[0]
    if len(z_range) == 0:
        logger.warning("  No se detecto cuerpo del paciente, saltando eliminacion")
        return
    z_min, z_max = z_range[0], z_range[-1]

    # Para cada slice axial, encontrar la componente mas grande (2D)
    for z in range(z_min, z_max + 1):
        slice_2d = body_mask[z, :, :]
        labeled, n_features = _label_connected_components_2d(slice_2d)
        if n_features < 1:
            continue
        # Mantener solo la componente mas grande
        sizes = np.bincount(labeled.ravel())
        if len(sizes) > 1:
            largest = np.argmax(sizes[1:]) + 1
            body_mask[z, :, :] = (labeled == largest).astype(np.uint8)

    logger.info(f"  Cuerpo detectado: slices {z_min}-{z_max}")

    # Paso 4: Eliminar camilla
    show_progress("Eliminando camilla...")
    for z in range(z_min, z_max + 1):
        slice_2d = body_mask[z, :, :].copy()
        rows_with_body = np.where(slice_2d.sum(axis=1) > 0)[0]
        if len(rows_with_body) == 0:
            continue
        bottom_row = rows_with_body[-1]
        # Limpiar filas debajo del cuerpo (ahi esta la camilla)
        if bottom_row < dims[1] - 3:
            body_mask[z, bottom_row + 1:, :] = 0
        # Recortar bordes laterales extremos
        cols_with_body = np.where(slice_2d.sum(axis=0) > 0)[0]
        if len(cols_with_body) > 0:
            left = cols_with_body[0]
            right = cols_with_body[-1]
            if left > 5:
                body_mask[z, :, :left - 2] = 0
            if right < dims[0] - 5:
                body_mask[z, :, right + 3:] = 0

    # Paso 5: Aplicar mascara al CT
    show_progress("Aplicando mascara al volumen...")
    ct_masked = ct_np.copy()
    ct_masked[body_mask == 0] = -1024  # HU de aire

    # Convertir de vuelta a VTK y asignar al nodo
    ct_masked_flat = ct_masked.ravel().astype(np.int16)
    vtk_arr = numpy_support.numpy_to_vtk(ct_masked_flat, deep=True)
    ct_img.GetPointData().SetScalars(vtk_arr)
    ct_img.Modified()

    body_voxels = body_mask.sum()
    total_voxels = body_mask.size
    logger.info(f"  ✓ Camilla y aire eliminados")
    logger.info(f"    Voxels cuerpo: {body_voxels} / {total_voxels} "
                f"({100 * body_voxels / total_voxels:.1f}%)")


def _label_connected_components_2d(binary_img):
    """
    Etiqueta componentes conectadas 2D (4-conectado).
    Returns: (labeled_array, num_features)
    """
    import numpy as np
    try:
        from scipy.ndimage import label
        return label(binary_img, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    except ImportError:
        # Fallback simple sin scipy
        labeled = np.zeros_like(binary_img, dtype=np.int32)
        label_count = 0
        for y in range(binary_img.shape[0]):
            for x in range(binary_img.shape[1]):
                if binary_img[y, x] and labeled[y, x] == 0:
                    label_count += 1
                    _flood_fill(binary_img, labeled, x, y, label_count)
        return labeled, label_count


def _flood_fill(binary, labeled, x0, y0, label_val):
    """Flood fill iterativo para etiquetado de componentes."""
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
