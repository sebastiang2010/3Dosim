"""
Paso 5: Escribir archivo .i MCNP final.

Combina las piezas generadas en los pasos anteriores:
  - Tarjetas de materiales (M)
  - Tarjetas de geometria (celdas + superficies)
  - Tarjetas de fuente (SDEF)
  - Tarjetas de tallies (FMESH4, F6, NPS, MODE)

Verifica el .i con 8 checks de validez.
"""

import logging
import os
import time

logger = logging.getLogger("3DosimTest")


def write_mcnp(geom_data: dict, source_data: dict, tally_data: dict,
               phantom_data: dict, output_dir: str):
    """
    Escribe el archivo .i MCNP a partir de las piezas pre-construidas.

    Args:
        geom_data: dict de geometry_builder.build_geometry()
            Debe contener: mat_cards, geom_cards
        source_data: dict de source_builder.build_source()
            Debe contener: source_cards, iso_data
        tally_data: dict de tally_builder.build_tallies()
            Debe contener: tally_cards
        phantom_data: dict de phantom_builder.build_phantom()
            Debe contener: dims, origin, spacing
        output_dir: Directorio de salida

    Returns:
        Ruta al archivo .i generado
    """
    logger.info("")
    logger.info("  ========================================================")
    logger.info("  [PASO 5/5] Escribiendo archivo MCNP .i")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    iso_data = source_data["iso_data"]
    mat_cards = geom_data["mat_cards"]
    geom_cards = geom_data["geom_cards"]
    source_cards = source_data["source_cards"]
    tally_cards = tally_data["tally_cards"]

    mcnp_dir = os.path.join(output_dir, "mcnp")
    os.makedirs(mcnp_dir, exist_ok=True)

    # Nombre del isotopo para el archivo
    iso_name = iso_data.get("name", "isotopo").replace("-", "_").replace(" ", "_")
    input_path = os.path.join(mcnp_dir, f"3Dosim_MCNP_{iso_name}.i")

    # Armar contenido
    lines = [
        f"3Dosim MCNP - {iso_data.get('name', 'Dosimetria')}",
        "C Generado por PipelineOrchestrator 3Dosim v3.14",
        f"C Isotopo: {iso_data.get('name', 'N/A')}  ZAID={iso_data.get('zaid', 0)}",
        f"C Particula: {iso_data.get('particle', '?')}  Modo: {iso_data.get('mode', '?')}",
        f"C Dimensiones: {phantom_data['dims']}",
        f"C Origen: {phantom_data['origin']}",
        f"C Espaciado: {phantom_data['spacing']}",
        "C",
        "C ============================================================",
        "C === MATERIALES ===",
        "C ============================================================",
    ]
    lines.extend(mat_cards)
    lines.append("C")
    lines.append("C ============================================================")
    lines.append("C === GEOMETRIA (celdas + superficies) ===")
    lines.append("C ============================================================")
    lines.extend(geom_cards)
    lines.append("C")
    lines.append("C ============================================================")
    lines.append("C === FUENTE ===")
    lines.append("C ============================================================")
    lines.extend(source_cards)
    lines.append("C")
    lines.append("C ============================================================")
    lines.append("C === TALLIES (detectores) ===")
    lines.append("C ============================================================")
    lines.extend(tally_cards)

    # Ultima linea en blanco
    lines.append("")

    with open(input_path, "w") as f:
        f.write("\n".join(lines))

    logger.info(f"  Archivo escrito: {input_path}")

    # Verificar
    verify_mcnp_input(input_path)

    elapsed = time.time() - t_start
    logger.info(f"  Archivo .i generado en {elapsed:.1f}s")
    return input_path


def verify_mcnp_input(path: str):
    """
    Verifica que el archivo .i MCNP sea valido.
    8 checks: header, M cards, geometria, SDEF, FMESH4, NPS, MODE, lattice.

    Args:
        path: Ruta al archivo .i

    Raises:
        RuntimeError: Si alguna verificacion falla
    """
    with open(path, "r") as f:
        content = f.read()

    checks = {
        "header": content.startswith("3Dosim"),
        "material_cards": any(
            line.strip().startswith("M") and " " in line
            for line in content.split("\n") if line.strip()
        ),
        "geometry_cards": "PX" in content or "RPP" in content,
        "source_cards": "SDEF" in content,
        "tally_cards": "FMESH4" in content,
        "nps_card": "NPS" in content,
        "mode_card": "MODE" in content,
        "has_lattice": "fill" in content,
    }

    all_ok = True
    for check_name, ok in checks.items():
        status = "+" if ok else "-"
        if ok:
            logger.info(f"  Verificacion {check_name}: {status}")
        else:
            logger.warning(f"  Verificacion {check_name}: {status}")
            all_ok = False

    line_count = content.count("\n") + 1
    file_size = os.path.getsize(path)
    logger.info(f"  Archivo: {line_count} lineas, {file_size/1024:.1f} KB")

    if not all_ok:
        raise RuntimeError("Archivo MCNP no paso las verificaciones")

    logger.info("  Archivo MCNP valido (todas las verificaciones OK)")
