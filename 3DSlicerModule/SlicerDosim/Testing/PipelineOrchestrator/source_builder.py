"""
Paso 2: Definir fuente desde PET.

Usa MCNPSourceBuilder de SlicerDosimLib para generar
las tarjetas SDEF a partir del volumen PET real.

Flujo:
  1. Obtener array PET del nodo de Slicer
  2. MCNPSourceBuilder.build() genera SDEF con distribucion espacial
  3. Retorna source_cards + iso_data
"""

import logging
import time

logger = logging.getLogger("3DosimTest")


def build_source(pet_node, phantom_data: dict, output_dir: str):
    """
    Define la fuente MCNP desde el PET y el phantom.

    Args:
        pet_node: vtkMRMLScalarVolumeNode del PET (o None para fuente uniforme)
        phantom_data: dict de phantom_builder.build_phantom()
        output_dir: Directorio de salida

    Returns:
        dict con:
            source_cards: list[str] para MCNP
            iso_data: dict con informacion del isotopo
    """
    import numpy as np
    import slicer

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  [PASO 2/5] Fuente desde PET")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    dims = phantom_data["dims"]

    # Isotopo por defecto: Y-90 (seleccionable en el futuro)
    iso_data = {
        "name": "Yttrium-90",
        "zaid": 39090,
        "energy_mev": 2.28,
        "particle": "electron",
        "mode": "e",
    }
    logger.info(f"  Isotopo: {iso_data['name']} (ZAID={iso_data['zaid']}, "
                f"E={iso_data['energy_mev']} MeV, particula={iso_data['particle']})")

    if pet_node is None:
        logger.warning("  PET no disponible, usando fuente uniforme en centro del volumen")
        logger.info("  Construyendo SDEF uniforme...")
        from SlicerDosim.SlicerDosimLib import MCNPSourceBuilder
        sb = MCNPSourceBuilder()
        source_cards = sb._build_sdef_uniform(dims, iso_data)
    else:
        logger.info(f"  PET encontrado: '{pet_node.GetName()}'")
        # Extraer info del PET
        pet_arr = slicer.util.arrayFromVolume(pet_node)
        logger.info(f"  PET array: {pet_arr.shape}, "
                    f"rango=[{pet_arr.min():.2f}, {pet_arr.max():.2f}]")

        # Crear mascara de higado para Y-90 (opcional)
        phantom_arr = phantom_data["phantom_arr"]
        liver_mask = (phantom_arr == 90)

        logger.info("  Construyendo SDEF desde PET...")
        from SlicerDosim.SlicerDosimLib import MCNPSourceBuilder
        sb = MCNPSourceBuilder()
        source_cards = sb.build(
            pet_volume_node=pet_node,
            dims=dims,
            iso_data=iso_data,
            liver_mask=liver_mask,
        )

    logger.info(f"  Tarjetas fuente generadas: {len(source_cards)}")
    for card in source_cards[:5]:
        logger.info(f"    {card}")
    if len(source_cards) > 5:
        logger.info(f"    ... y {len(source_cards)-5} mas")

    elapsed = time.time() - t_start
    logger.info(f"  Fuente definida en {elapsed:.1f}s")

    return {
        "source_cards": source_cards,
        "iso_data": iso_data,
    }
