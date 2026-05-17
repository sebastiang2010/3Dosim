"""
Paso 3: Construir geometria MCNP voxelizada.

Usa MCNPGeometryBuilder de SlicerDosimLib para generar
tarjetas de celdas y superficies (LIKE n BUT, RPP, lattice fill).

Flujo:
  1. MCNPMaterialMapper asigna materiales desde phantom_arr
  2. MCNPGeometryBuilder.build() genera tarjetas de geometria
  3. Retorna mat_cards + geom_cards + material_ids
"""

import logging
import time

logger = logging.getLogger("3DosimTest")


def build_geometry(phantom_data: dict, output_dir: str):
    """
    Construye la geometria voxelizada MCNP desde el phantom.

    Args:
        phantom_data: dict de phantom_builder.build_phantom()
            Debe contener: phantom_arr, dims, origin, spacing
        output_dir: Directorio de salida

    Returns:
        dict con:
            mat_cards: list[str] tarjetas M
            geom_cards: list[str] tarjetas de geometria
            material_ids: set[int] materiales usados
    """
    import numpy as np

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  [PASO 3/5] Geometria voxelizada MCNP")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    phantom_arr = phantom_data["phantom_arr"]
    dims = phantom_data["dims"]
    origin = phantom_data["origin"]
    spacing = phantom_data["spacing"]

    from SlicerDosim.SlicerDosimLib import (
        TissueConfig, MCNPMaterialMapper, MCNPGeometryBuilder
    )

    config = TissueConfig()

    # 1. Asignar materiales
    logger.info("  [A] Asignando materiales MCNP desde phantom...")
    mapper = MCNPMaterialMapper(config)
    mat_arr = mapper.assign_from_labelmap(phantom_arr)
    material_ids = mapper.get_material_ids_used()
    mat_cards = mapper.generate_material_cards()
    logger.info(f"      Materiales MCNP usados: {sorted(material_ids)}")
    logger.info(f"      Tarjetas M generadas: {len(mat_cards)}")
    for card in mat_cards:
        logger.info(f"      {card[:80]}")

    # 2. Construir geometria
    logger.info("  [B] Construyendo geometria voxelizada...")
    geo_builder = MCNPGeometryBuilder(config)
    geom_cards = geo_builder.build(dims, origin, spacing, mat_arr)
    logger.info(f"      Tarjetas geometria: {len(geom_cards)}")

    # Contar tipos de celda
    cell_count = sum(1 for c in geom_cards if c.strip().startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")) and " " in c[:5])
    surf_count = sum(1 for c in geom_cards if "PX " in c or "PY " in c or "PZ " in c)
    logger.info(f"      Celdas: ~{cell_count}, Superficies: ~{surf_count}")

    elapsed = time.time() - t_start
    logger.info(f"  Geometria construida en {elapsed:.1f}s")

    return {
        "mat_cards": mat_cards,
        "geom_cards": geom_cards,
        "material_ids": material_ids,
    }
