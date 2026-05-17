"""
Paso 4: Configurar detectores (tallies) MCNP.

Usa MCNPTallyBuilder de SlicerDosimLib para generar
FMESH4, F6, DE4/DF4, NPS y MODE.

Flujo:
  1. MCNPTallyBuilder.build() con iso_data + dims
  2. Retorna tally_cards
"""

import logging
import time

logger = logging.getLogger("3DosimTest")


def build_tallies(source_data: dict, phantom_data: dict, output_dir: str):
    """
    Configura los detectores MCNP para el calculo de dosis.

    Args:
        source_data: dict de source_builder.build_source()
            Debe contener: iso_data
        phantom_data: dict de phantom_builder.build_phantom()
            Debe contener: dims, origin, spacing
        output_dir: Directorio de salida

    Returns:
        dict con:
            tally_cards: list[str] tarjetas de tallies
    """
    import numpy as np

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  [PASO 4/5] Detectores (tallies) MCNP")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    iso_data = source_data["iso_data"]
    dims = phantom_data["dims"]
    origin = phantom_data["origin"]

    logger.info(f"  Isotopo: {iso_data['name']}")
    logger.info(f"  Particula: {iso_data['particle']}, Modo: {iso_data['mode']}")
    logger.info(f"  Dimensiones malla: {dims[0]}x{dims[1]}x{dims[2]}")
    logger.info(f"  Particulas (NPS): 10⁷")

    from SlicerDosim.SlicerDosimLib import MCNPTallyBuilder

    tb = MCNPTallyBuilder()
    tally_cards = tb.build(
        iso_data=iso_data,
        dims=dims,
        n_particles=10_000_000,
        origin=origin,
    )

    logger.info(f"  Tarjetas tallies generadas: {len(tally_cards)}")

    # Mostrar resumen de tarjetas principales
    for card in tally_cards:
        stripped = card.strip()
        if stripped.startswith(("FMESH", "F6", "DE", "DF", "NPS", "MODE", "CUT")):
            logger.info(f"    {stripped[:80]}")

    elapsed = time.time() - t_start
    logger.info(f"  Tallies configurados en {elapsed:.1f}s")

    return {
        "tally_cards": tally_cards,
    }
