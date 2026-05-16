"""
Generacion y verificacion de entrada MCNP (Modulo 2).

Construye el archivo .i completo:
  - Materiales (M cards)
  - Geometria (RPP, lattice fill)
  - Fuente (SDEF desde PET)
  - Tallies (FMESH4, F6, modo, NPS)
  - Verificacion de 8 checks de validez
"""

import logging
import os

logger = logging.getLogger("3DosimTest")


def generate_mcnp_input(ct_node, output_dir: str, data_dir: str = None):
    """
    Genera entrada MCNP y verifica el .i.
    Usa arrays numpy directamente para construir el phantom.

    Args:
        ct_node: vtkMRMLScalarVolumeNode del CT
        output_dir: Directorio donde guardar el .i
        data_dir: Directorio de datos (opcional, para PET)

    Returns:
        Ruta al archivo .i generado
    """
    import numpy as np
    from SlicerDosim.SlicerDosimLib import (
        MCNPMaterialMapper, MCNPGeometryBuilder,
        MCNPTallyBuilder, TissueConfig
    )

    config = TissueConfig()
    dims = ct_node.GetImageData().GetDimensions()
    origin = ct_node.GetOrigin()
    spacing = ct_node.GetSpacing()

    mcnp_dir = os.path.join(output_dir, "mcnp")
    if not os.path.exists(mcnp_dir):
        os.makedirs(mcnp_dir)

    logger.info("  Creando phantom array...")

    # Phantom simplificado: elipse de higado (90) + tumor (100)
    step = 4
    sx, sy, sz = dims[0] // step, dims[1] // step, dims[2] // step
    phantom_arr = np.ones((sx, sy, sz), dtype=np.uint8)
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    # Elipse higado
    rx, ry, rz = sx // 4, sy // 4, sz // 3
    for z in range(max(0, cz - rz), min(sz, cz + rz)):
        for y in range(sy):
            for x in range(sx):
                dx, dy, dz = (x - cx) / rx, (y - cy) / ry, (z - cz) / rz
                if dx * dx + dy * dy + dz * dz <= 1:
                    phantom_arr[x, y, z] = 90

    # Esfera tumor
    tcx, tcy, tcz = cx + rx // 2, cy, cz
    tr = sx // 16
    for z in range(max(0, tcz - tr), min(sz, tcz + tr)):
        for y in range(sy):
            for x in range(sx):
                dx, dy, dz = x - tcx, y - tcy, z - tcz
                if dx * dx + dy * dy + dz * dz <= tr * tr:
                    phantom_arr[x, y, z] = 100

    logger.info(f"  Phantom array: {sx}x{sy}x{sz}")
    logger.info(f"  Indices: {sorted(np.unique(phantom_arr))}")

    # --- Materiales ---
    logger.info("  [A] Asignando materiales...")
    mapper = MCNPMaterialMapper(config)
    mat_arr = mapper.assign_from_labelmap(phantom_arr)
    mat_cards = mapper.generate_material_cards()
    logger.info(f"      Materiales: {sorted(mapper.get_material_ids_used())}")
    logger.info(f"      Tarjetas M: {len(mat_cards)}")

    # --- Geometria ---
    logger.info("  [B] Construyendo geometria...")
    geo_builder = MCNPGeometryBuilder(config)
    geom_cards = geo_builder.build((sx, sy, sz), origin, spacing, mat_arr)
    logger.info(f"      Tarjetas geometria: {len(geom_cards)}")

    # --- Tallies ---
    logger.info("  [C] Configurando tallies...")
    iso_data = {
        "name": "Yttrium-90", "zaid": 39090, "energy_mev": 2.28,
        "particle": "electron", "mode": "e",
    }
    tal_builder = MCNPTallyBuilder()
    tal_cards = tal_builder.build(iso_data, (sx, sy, sz), n_particles=1000000, origin=origin)
    logger.info(f"      Tarjetas tallies: {len(tal_cards)}")

    # --- Escribir archivo .i ---
    logger.info("  [D] Escribiendo archivo .i...")
    input_path = os.path.join(mcnp_dir, "3Dosim_MCNP_Y90.i")
    _write_i_file(input_path, mat_cards, geom_cards, tal_cards)

    # Verificar
    verify_mcnp_input(input_path)
    logger.info(f"  MCNP input generado: {input_path}")
    return input_path


def _write_i_file(path: str, mat_cards, geom_cards, tal_cards):
    """Escribe archivo .i MCNP formateado."""
    src_cards = [
        "C FUENTE uniforme (placeholder)",
        "SDEF  POS=0 0 0  ERG=D1  PAR=2",
        "SI1  L  0.9357  2.2807",
        "SP1  D  1.0  0.0",
    ]
    lines = [
        "3Dosim MCNP test - SlicerDosim",
        "C Generado por PipelineOrchestrator",
    ]
    lines.append("C")
    lines.append("C ===== MATERIALES =====")
    lines.extend(mat_cards)
    lines.append("C")
    lines.append("C ===== GEOMETRIA =====")
    lines.extend(geom_cards)
    lines.append("C")
    lines.append("C ===== FUENTE =====")
    lines.extend(src_cards)
    lines.append("C")
    lines.append("C ===== TALLIES =====")
    lines.extend(tal_cards)

    with open(path, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")
    logger.info(f"  .i escrito: {path}")


def verify_mcnp_input(path: str):
    """
    Verifica que el archivo .i MCNP sea valido.
    Chequea 8 condiciones: header, M cards, geometria, SDEF, FMESH4, NPS, MODE, lattice.

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
    logger.info(f"  Archivo: {line_count} lineas, {len(content)} caracteres")

    if not all_ok:
        raise RuntimeError("Archivo MCNP no paso las verificaciones")

    logger.info("  Archivo MCNP valido")
