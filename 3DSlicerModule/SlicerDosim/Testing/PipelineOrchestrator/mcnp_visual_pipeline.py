#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcnp_visual_pipeline.py - Pipeline visual de generacion de input MCNP.
Version independiente (NO necesita Slicer).

Muestra paso a paso como se construye un archivo de entrada MCNP
a partir de segmentacion CT/PET en 3Dosim.

Uso:
    python mcnp_visual_pipeline.py                          # usa ejemplo incluido
    python mcnp_visual_pipeline.py --file ruta/al/archivo.i # archivo .i existente
    python mcnp_visual_pipeline.py --synthetic              # genera mini-ejemplo sintetico
    python mcnp_visual_pipeline.py --steps 1-5              # solo pasos 1 a 5
    python mcnp_visual_pipeline.py --ruflo                   # usa ruflo memory para tracking
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import textwrap
from datetime import datetime
from typing import Optional

# Forzar UTF-8 en consola Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Caracteres seguros para Windows (ASCII)
_H  = "="  # horizontal
_V  = "|"  # vertical
_TL = "+"  # top-left
_TR = "+"  # top-right
_BL = "+"  # bottom-left
_BR = "+"  # bottom-right
_LV = "+"  # left vertical
_RV = "+"  # right vertical
_TD = "+"  # top-down
_BU = "+"  # bottom-up
_X  = "+"  # cross
_B  = "#"  # block fill
_E  = "."  # empty fill


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════════

EXAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..",
    "ej_mcnp", "3Dosim_MCNP_Y90_universos.i"
)

PASOS = [
    "1.  VOLUMEN CT",
    "2.  LABELMAP PHANTOM",
    "3.  ARRAY PET",
    "4.  HEADER (comentarios)",
    "5.  UNIVERSOS (LIKE n BUT)",
    "6.  LATTICE + RLE",
    "7.  SUPERFICIES",
    "8.  MODE / PHYS / CUT",
    "9.  FUENTE (SDEF)",
    "10. TALLIES (TMESH)",
    "11. MATERIALES",
    "12. FOOTER (RAND / NPS)",
]

SECCION_MARCADORES = {
    1:  (r"^c\s+Universos", "HEADER"),
    2:  (r"^1\s+1\s+-0\.001205", "UNIVERSO_AIRE"),
    3:  (r"like\s+1\s+but", "UNIVERSOS_LIKE"),
    4:  (r"fill=101", "LATTICE"),
    5:  (r"lat=1", "LATTICE_CARD"),
    6:  (r"^\s+\d+\s*r\s", "RLE_DATA"),
    7:  (r"rpp", "SUPERFICIE_RPP"),
    8:  (r"so\s+15", "ESFERA_SO650"),
    9:  (r"^mode\s+e", "MODE"),
    10: (r"^sdef\s+", "SOURCE_SDEF"),
    11: (r"^si5\s+l", "VOXEL_FUENTE"),
    12: (r"^tmesh", "TALLIES"),
    13: (r"^m1\s+", "MATERIAL_AIRE"),
    14: (r"^rand\s+stride", "RAND"),
    15: (r"^NPS\s+", "NPS"),
}


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES VISUALES
# ═══════════════════════════════════════════════════════════════════════════

def c(text: str, color: str = "cyan") -> str:
    """Colorea texto para terminal (ANSI)."""
    colores = {
        "cyan": "\033[96m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    return f"{colores.get(color, '')}{text}{colores['reset']}"


def separador(titulo: str = "", char: str = "") -> None:
    w = 74
    cchar = char if char else _H
    if titulo:
        lado = (w - len(titulo) - 2) // 2
        print(f"\n{cchar * lado} {c(titulo, 'bold')} {cchar * lado}")
    else:
        print(cchar * w)


def caja(texto: str, color: str = "cyan") -> None:
    """Dibuja una caja alrededor del texto."""
    lines = texto.split("\n")
    w = max(len(l) for l in lines) + 4
    top = _TL + _H * w + _TR
    mid = _V
    bot = _BL + _H * w + _BR
    print(f"\n{c(top, color)}")
    for l in lines:
        print(f"{c(mid, color)} {l.ljust(w - 2)} {c(mid, color)}")
    print(f"{c(bot, color)}")


def tabla(headers: list, rows: list) -> None:
    """Dibuja una tabla ASCII."""
    col_w = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_w[i] = max(col_w[i], len(str(cell)))
    sep = _H * (sum(col_w) + 3 * len(headers) + 1)
    print(f"  {_TL}{sep}{_TR}")
    hdr = f"  {_V}"
    for i, h in enumerate(headers):
        hdr += f" {h.center(col_w[i])} {_V}"
    print(hdr)
    print(f"  {_LV}{sep}{_RV}")
    for row in rows:
        line = f"  {_V}"
        for i, cell in enumerate(row):
            line += f" {str(cell).ljust(col_w[i])} {_V}"
        print(line)
    print(f"  {_BL}{sep}{_BR}")


def progreso(paso: int, total: int = 12) -> str:
    """Barra de progreso unicode."""
    filled = "▓" * paso
    empty = "░" * (total - paso)
    return f"[{filled}{empty}] {paso}/{total}"


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE STEPS
# ═══════════════════════════════════════════════════════════════════════════

def step_1_volumen_ct(data: dict) -> dict:
    """Paso 1: Informacion del volumen CT."""
    separador("PASO 1: VOLUMEN CT", "─")
    caja("El primer paso es extraer dimensiones, origen y espaciado\n"
         "del volumen CT. Estos definen la geometria del lattice MCNP.",
         "cyan")

    dims = data.get("dims", (512, 512, 171))
    spacing = data.get("spacing", (0.98, 0.98, 2.0))
    nx, ny, nz = dims
    sx, sy, sz = spacing

    tabla(
        ["Parametro", "Valor", "Unidad"],
        [
            ["Voxeles X", str(nx), "vox"],
            ["Voxeles Y", str(ny), "vox"],
            ["Voxeles Z", str(nz), "vox"],
            ["Spacing X", f"{sx:.2f}", "mm"],
            ["Spacing Y", f"{sy:.2f}", "mm"],
            ["Spacing Z", f"{sz:.2f}", "mm"],
            ["Tamano X", f"{nx * sx / 10:.1f}", "cm"],
            ["Tamano Y", f"{ny * sy / 10:.1f}", "cm"],
            ["Tamano Z", f"{nz * sz / 10:.1f}", "cm"],
            ["Volumen total", f"{nx * sx * ny * sy * nz * sz / 1000:.0f}", "cm³"],
        ],
    )

    print(c(f"\n  → Dimension total: {nx} × {ny} × {nz} voxeles", "green"))
    print(c(f"  → Esto genera un lattice de {nx * ny * nz:,} celdas", "dim"))
    return {"step": 1, "dims": dims, "spacing": spacing}


def step_2_phantom_labelmap(data: dict) -> dict:
    """Paso 2: Conversion de segmentacion a indices phantom."""
    separador("PASO 2: LABELMAP PHANTOM", "─")
    caja("Cada organo segmentado por TotalSegmentator se mapea a un\n"
         "indice numerico (phantom index). Estos indices determinan\n"
         "que material MCNP tendra cada voxel en la simulacion.",
         "cyan")

    mapping = {
        1: "Aire (fondo)", 30: "Tejido blando (organos)",
        50: "Pulmon", 80: "Hueso",
        90: "Higado", 100: "Tumor",
    }

    rows = []
    for idx, desc in mapping.items():
        rows.append([str(idx), desc, "2 (Tejido)" if idx != 1 else "1 (Aire)"])

    tabla(["Indice Phantom", "Organo", "Material MCNP"], rows)

    # Mostrar el mapeo de nombres
    ts_map = {
        "spleen": 30, "kidney": 30, "liver": 90, "lung": 50,
        "vertebra": 80, "tumor": 100,
    }
    print(c(f"\n  → Regla de asignacion:", "yellow"))
    print(f"    Si el nombre del segmento contiene 'liver' → indice 90")
    print(f"    Si contiene 'lung' → indice 50")
    print(f"    Si contiene 'vertebra'/'rib'/'scapula' → indice 80")
    print(f"    Si contiene 'tumor' → indice 100")
    print(f"    Otros organos → indice 30 (tejido blando)")
    print(f"    Vacio/fuera del cuerpo → indice 1 (aire)")
    print(c(f"\n  → Los indices phantom se usan para crear universos MCNP", "green"))
    return {"step": 2}


def step_3_pet_array(data: dict) -> dict:
    """Paso 3: Extraccion del array PET."""
    separador("PASO 3: ARRAY PET", "─")
    caja("El volumen PET contiene la distribucion de actividad del\n"
         "radiofarmaco. Se usa para ponderar la fuente en MCNP.\n"
         "Si no hay PET, la fuente es uniforme en todo el cuerpo.",
         "cyan")

    has_pet = data.get("has_pet", True)
    if has_pet:
        print(c("  ✓ PET disponible:", "green"))
        print("    - Se multiplica por la mascara del cuerpo (phantom > 0)")
        print("    - Solo voxeles con actividad > 0 se incluyen como fuente")
        print("    - Cada voxel es una fuente con peso proporcional a su actividad")
    else:
        print(c("  ⚠ SIN PET:", "yellow"))
        print("    - Fuente uniforme en todos los voxeles del cuerpo")
        print("    - Todos los voxeles no-aire pesan igual")

    print(c("\n  → La fuente activa tiene ~N voxeles:", "dim"))
    print("    - Cada voxel se declara en si5/sp5 con formato:")
    print(c("      (mat_id<102[ ix iy iz ]<101)", "cyan"))
    print("    - Los pesos sp5 suman 1.0 (distribucion normalizada)")
    return {"step": 3}


def step_4_header(data: dict) -> dict:
    """Paso 4: Cabecera del archivo."""
    separador("PASO 4: HEADER (COMENTARIOS)", "─")
    caja("El archivo MCNP comienza con una cabecera de comentarios.\n"
         "Toda linea que empieza con 'c' es un comentario en MCNP.",
         "cyan")

    header = textwrap.dedent("""\
    c ------------------------------------------------------
    c Archivo generado con 3Dosim, version 3.14
    c Fecha : 17-Jun-2026 12:00 hs
    c ------------------------------------------------------
    c Isotopo: Y-90 (Yttrium-90)
    c   ZAID: 39090, T1/2: 2.67 dias, Emax: 2.28 MeV
    c ------------------------------------------------------
    c
    c Universos""")

    print(c("  Contenido del header:", "yellow"))
    for line in header.split("\n"):
        print(c(f"  {line}", "dim"))

    cols = [
        ["c", "Comentario", "Ignorado por MCNP"],
        ["c Universos", "Inicio de seccion", "Solo documentacion"],
    ]
    tabla(["Prefijo", "Significado", "Efecto"], cols)

    iso = data.get("isotope", "Y-90")
    iso_data = {
        "Y-90": ("Yttrium-90", 39090, 2.67, 2.2807),
        "I-131": ("Iodine-131", 53131, 8.02, 0.606),
        "Lu-177": ("Lutetium-177", 77177, 6.65, 0.498),
        "Tc-99m": ("Technetium-99m", 43099, 0.25, 0.140),
    }
    name, zaid, half_life, emax = iso_data.get(iso, iso_data["Y-90"])

    datos_iso = [
        ["Isotopo", iso],
        ["Nombre", name],
        ["ZAID", str(zaid)],
        ["T1/2 (dias)", f"{half_life:.2f}"],
        ["E_max (MeV)", f"{emax:.4f}"],
    ]
    tabla(["Propiedad", "Valor"], datos_iso)

    print(c(f"\n  → El ZAID {zaid} se usaria en la tarjeta de material", "dim"))
    print(c(f"  → La energia maxima {emax} MeV controla phys:p y phys:e", "dim"))
    return {"step": 4}


def step_5_universos(data: dict) -> dict:
    """Paso 5: Definicion de universos LIKE n BUT."""
    separador("PASO 5: UNIVERSOS (LIKE n BUT)", "─")
    caja("Cada organo/tejido tiene su propio universo MCNP.\n"
         "El universo 1 (aire) es la referencia. Los demas\n"
         "se definen como 'like 1 but' con diferente material.",
         "cyan")

    print(c("  Estructura de universo:", "yellow"))
    print(textwrap.dedent("""\
      ┌─ Cell card:  <id>  <mat>  <rho>  -<surf>  u=<U>  imp:p=<n>
      │
      │  1    1   -0.001205   -650   u=1   imp:p=1 imp:e=1   $ Aire
      │  │    │      │         │      │         │
      │  │    │      │         │      └─ Universo 1
      │  │    │      └─ Superficie -650 (dentro de la esfera SO 650)
      │  │    └─ Densidad negativa = g/cm³
      │  └─ Numero de celda
      │
      │  30  like 1 but  mat=2  rho=-1.06  u=30  imp:p=1  $ Tejido blando
      │       └── HERE: hereda geometria del universo 1,
      │            solo cambia material y densidad
      └─"""))

    indices = [
        ("1", "1", "0.001205", "Aire Dry"),
        ("30", "2", "1.06", "Tejido blando (ICRU 44)"),
        ("50", "2", "1.06", "Pulmon"),
        ("80", "2", "1.06", "Hueso"),
        ("90", "2", "1.06", "Higado"),
        ("100", "2", "1.06", "Tumor"),
    ]
    tabla(
        ["Universo", "Material", "Rho (g/cm³)", "Tejido"],
        indices,
    )

    print(c("\n  → La esfera SO 650 de radio 15 cm contiene todo", "green"))
    print(c("  → No hay 'closure cells': el voxel fuera de la esfera = 0 importancia", "dim"))
    print(c("  → LIKE n BUT evita repetir geometria para cada organo", "bold"))
    return {"step": 5}


def step_6_lattice_rle(data: dict) -> dict:
    """Paso 6: Lattice y RLE fill."""
    separador("PASO 6: LATTICE + RLE", "─")
    caja("El lattice es una matriz 3D de voxeles. Cada voxel\n"
         "contiene el indice del universo que le corresponde.\n"
         "RLE (Run-Length Encoding) comprime la matriz evitando\n"
         "escribir cada voxel individualmente.",
         "cyan")

    dims = data.get("dims", (512, 512, 171))
    nx, ny, nz = dims

    print(c("  Estructura del lattice:", "yellow"))
    print(textwrap.dedent("""\
    101   0   -1            fill=101     imp:p=1    ← Wrapper exterior
    102   0   -2   lat=1    u=101        imp:p=1    ← Lattice card
                       fill=0:NX 0:NY 0:NZ          ← Rango del lattice
          <datos RLE>                               ← Fill comprimido
    9999  0    1            imp:p=0 imp:e=0         ← Outside world
    """))

    # Estimar compresion RLE
    total_voxels = nx * ny * nz
    estimated_rle_lines = math.ceil(total_voxels / 200)
    compression_ratio = 4  # estimado: cada valor se reemplaza por run-length
    rle_tokens = math.ceil(total_voxels / compression_ratio)

    comp = [
        ["Voxeles totales", f"{total_voxels:,}"],
        ["Tokens RLE (estimado)", f"{rle_tokens:,}"],
        ["Lineas RLE (estimado)", f"{estimated_rle_lines:,}"],
        ["Compresion aprox", f"{compression_ratio}:1"],
    ]
    tabla(["Metrica", "Valor"], comp)

    print(c("\n  Ejemplo RLE:", "yellow"))
    print(c("    Formato: <n>r = repetir el ultimo valor n veces", "green"))
    print(textwrap.dedent("""\\
      1 48364r 30 35r 1 10r 30 9r
      │   │     │  │   │  │   │  └── 30 repetido 9 veces
      │   │     │  │   │  └── 1 repetido 10 veces
      │   │     │  └── 30 repetido 35 veces
      │   └── 48364 voxeles con valor 1 (aire)
      └── Primer voxel de la fila = 1 (aire)
    """))

    if data.get("flip_rows", False):
        print(c("  ⚠ Flip Y activado: invierte eje Y antes de RLE", "yellow"))
        print("    (Para compatibilidad con ordenamiento MATLAB)")

    # Diagrama conceptual
    print(c("\n  Diagrama conceptual del lattice 3D:", "bold"))
    z_slice = min(nz // 2, 10)
    print(textwrap.dedent(f"""\\
        Corte axial en z={z_slice}:
        +-----------------------------+
        | 1 1 1 1 1 1 1 1 1 1 1 1 1 1|  <- aire (fondo)
        | 1 1 1 1 30 30 30 30 1 1 1 1|  <- tejido (organos)
        | 1 1 30 30 30 30 30 30 30 1 1|
        | 1 30 30 90 90 90 90 30 30 1|  <- higado (indice 90)
        | 1 30 90 90 100 90 90 30 1 1|  <- tumor (indice 100)
        | 1 30 90 90 90 90 30 30 1 1 1|
        | 1 1 30 30 30 30 30 30 1 1 1|
        | 1 1 1 30 30 30 30 1 1 1 1 1|
        | 1 1 1 1 1 1 1 1 1 1 1 1 1 1|
        +-----------------------------+
        Cada numero = indice de universo = material
    """))
    return {"step": 6}


def step_7_surfaces(data: dict) -> dict:
    """Paso 7: Superficies MCNP."""
    separador("PASO 7: SUPERFICIES", "─")
    caja("MCNP necesita superficies para delimitar las celdas.\n"
         "En 3Dosim se usan 3 superficies: el bounding box (RPP),\n"
         "el voxel unitario (RPP), y la esfera boundary (SO).",
         "cyan")

    dims = data.get("dims", (512, 512, 171))
    spacing = data.get("spacing", (0.98, 0.98, 2.0))
    nx, ny, nz = dims
    sx, sy, sz = spacing
    xm = round(nx * sx / 10, 4)
    ym = round(ny * sy / 10, 4)
    zm = round(nz * sz / 10, 4)
    sx_cm = round(sx / 10, 4)
    sy_cm = round(sy / 10, 4)
    sz_cm = round(sz / 10, 4)

    print(c("  Tarjetas de superficie:", "yellow"))
    print(textwrap.dedent(f"""\\
    1   rpp  0.  {xm}  0.  {ym}  0.  {zm}    ← Bounding box del phantom
    2   rpp  0.  {sx_cm}  0. {sy_cm}  0. {sz_cm}  ← Voxel unitario
    650 so  15                                  ← Esfera de 15 cm radio
    """))

    surf = [
        ["1", f"RPP", f"0 → {xm}", f"0 → {ym}", f"0 → {zm}", "Bounding box"],
        ["2", f"RPP", f"0 → {sx_cm}", f"0 → {sy_cm}", f"0 → {sz_cm}", "Voxel unitario"],
        ["650", "SO", "n/a", "n/a", "n/a", f"Esfera r=15"],
    ]
    tabla(["#", "Tipo", "X (cm)", "Y (cm)", "Z (cm)", "Uso"], surf)

    print(c(f"\n  → Bounding box: {xm} × {ym} × {zm} cm³", "green"))
    print(c(f"  → Voxel unitario: {sx_cm} × {sy_cm} × {sz_cm} cm³", "dim"))
    print(c(f"  → Esfera SO 650: boundary que contiene todo el phantom", "dim"))
    return {"step": 7}


def step_8_mode(data: dict) -> dict:
    """Paso 8: Mode, PHYS y CUT."""
    separador("PASO 8: MODE / PHYS / CUT", "─")
    caja("Definen el tipo de particulas a simular, los limites\n"
         "fisicos y los cortes de energia. Para dosimetria de\n"
         "radionucleidos se usan electrones (e) y fotones (p).",
         "cyan")

    iso = data.get("isotope", "Y-90")
    e_max = {"Y-90": 2.2807, "I-131": 0.606, "Lu-177": 0.498, "Tc-99m": 0.140}.get(iso, 2.2807)

    print(c(f"  Para {iso} (E_max = {e_max} MeV):", "yellow"))
    print(textwrap.dedent(f"""\\
    mode e p                                ← Particulas: electrones + fotones
    phys:p {e_max} J J J J J J              ← Limite superior foton
    phys:e {e_max} J J J J J J J J J J J J 0.99  ← Limite superior electron
    cut:p J 1e-3                             ← Cut de energia fotones (1 keV)
    cut:e J 1e-3                             ← Cut de energia electrones (1 keV)
    """))

    mode_table = [
        ["mode e p", "Simular electrones y fotones"],
        ["phys:p E_max ...", "Limite fisico para fotones"],
        ["phys:e E_max ...", "Limite fisico para electrones transportados"],
        ["cut:p J 1e-3", "E<1 keV: fotones se matan (depositan energia local)"],
        ["cut:e J 1e-3", "E<1 keV: electrones se matan"],
    ]
    tabla(["Tarjeta", "Efecto"], mode_table)
    print(c(f"\n  → El ultimo parametro de phys:e (0.99) activa el Straggling", "dim"))
    return {"step": 8}


def step_9_source(data: dict) -> dict:
    """Paso 9: Definicion de fuente SDEF."""
    separador("PASO 9: FUENTE (SDEF)", "─")
    caja("La fuente define donde y como se emiten las particulas.\n"
         "3Dosim usa una distribucion voxelizada: cada voxel activo\n"
         "es una sub-fuente con posicion y peso especificos.",
         "cyan")

    print(c("  SDEF basica:", "yellow"))
    print(textwrap.dedent("""\\
    sdef par=d1 wgt=1.000... erg=fpar=d6 x=d2 y=d3 z=d4 cell=d5
    read file Y90cel3D.src      ← Archivo externo con espectro + distribucion angular
    """))

    print(c("  Distribucion en el voxel:", "yellow"))
    sx_cm = round(data.get("spacing", (0.98, 0.98, 2.0))[0] / 10, 4)
    sy_cm = round(data.get("spacing", (0.98, 0.98, 2.0))[1] / 10, 4)
    sz_cm = round(data.get("spacing", (0.98, 0.98, 2.0))[2] / 10, 4)
    print(textwrap.dedent(f"""\\
    si2 h 0. {sx_cm}          ← distribucion uniforme X en el voxel
    sp2 d 0 1
    si3 h 0. {sy_cm}          ← distribucion uniforme Y en el voxel
    sp3 d 0 1
    si4 h 0. {sz_cm}          ← distribucion uniforme Z en el voxel
    sp4 d 0 1
    """))

    print(c("  Voxeles fuente (si5/sp5):", "yellow"))
    print("""\
    si5 l  (90<102[0 0 0]<101) (90<102[1 0 0]<101) ...
    sp5     0.0001  0.0001  0.0001  ...
    """)

    print(c("  Formato de cada entrada si5:", "bold"))
    print("    (MAT<102[ IX  IY  IZ ]<101")
    print("     │    │    │   │   └── Lattice index Z")
    print("     │    │    │   └────── Lattice index Y")
    print("     │    │    └────────── Lattice index X")
    print("     │    └── Celda 102 = lattice card")
    print("     └── Material (phantom index)")

    print(c("\n  → El archivo .src externo contiene el espectro completo", "dim"))
    print(c("  → sp5 pesos suman 1 (normalizado)", "dim"))
    return {"step": 9}


def step_10_tallies(data: dict) -> dict:
    """Paso 10: Tallies TMESH."""
    separador("PASO 10: TALLIES (TMESH)", "─")
    caja("Los tallies registran la dosis depositada. 3Dosim usa\n"
         "TMESH F6 (energia depositada por gramo) en una malla\n"
         "que coincide con los voxeles del CT.",
         "cyan")

    dims = data.get("dims", (512, 512, 171))
    spacing = data.get("spacing", (0.98, 0.98, 2.0))
    nx, ny, nz = dims
    xm = round(nx * spacing[0] / 10, 4)
    ym = round(ny * spacing[1] / 10, 4)
    zm = round(nz * spacing[2] / 10, 4)

    print(c("  Tallies TMESH:", "yellow"))
    print(textwrap.dedent(f"""\\
    tmesh
    rmesh1:e   pedep              ← F6: MeV/(cm³ * source_particle)
    cora1  0  {nx-1}i  {xm}       ← Malla X: {nx} divisiones
    corb1  0  {ny-1}i  {ym}       ← Malla Y: {ny} divisiones
    corc1  0  {nz-1}i  {zm}       ← Malla Z: {nz} divisiones
    endmd
    """))

    tallies = [
        ["rmesh1:e", "pedep", f"F6 (MeV/g por particula fuente)"],
        ["cora1", f"0 → {xm}", f"{nx} bins en X"],
        ["corb1", f"0 → {ym}", f"{ny} bins en Y"],
        ["corc1", f"0 → {zm}", f"{nz} bins en Z"],
    ]
    tabla(["Tarjeta", "Rango", "Division"], tallies)

    print(c(f"\n  → La malla de tallies coincide voxel a voxel con el CT", "green"))
    print(c(f"  → Total: {nx} × {ny} × {nz} = {nx*ny*nz:,} voxeles de dosis", "dim"))
    print(c(f"  → F6 deposita energia en MeV/g - se convierte a Gy", "dim"))
    return {"step": 10}


def step_11_materials(data: dict) -> dict:
    """Paso 11: Materiales MCNP."""
    separador("PASO 11: MATERIALES", "─")
    caja("Los materiales definen la composicion atomica de cada\n"
         "tejido. 3Dosim usa 2 materiales base: aire y tejido\n"
         "blando (ICRU 44). Las fracciones son negativas = peso.",
         "cyan")

    print(c("  m1 - Aire Dry (near sea level):", "yellow"))
    print("""\
    m1    6000  -0.000124      $ C (Carbono)
          7000  -0.755268      $ N (Nitrogeno)
          8000  -0.231481      $ O (Oxigeno)
          18000 -0.012827      $ Ar (Argon)""")

    print(c("  m2 - Soft Tissue (ICRU 44):", "yellow"))
    print("""\
    m2    1000  -0.105         $ H (Hidrogeno)
          6000  -0.143         $ C (Carbono)
          7000  -0.034         $ N (Nitrogeno)
          8000  -0.708         $ O (Oxigeno)
          11000 -0.002         $ Na (Sodio)
          15000 -0.003         $ P (Fosforo)
          16000 -0.003         $ S (Azufre)
          17000 -0.002         $ Cl (Cloro)
          19000 -0.003         $ K (Potasio)""")

    comp_rows = [
        ["m1", "Aire", "0.001205", "C, N, O, Ar", "4"],
        ["m2", "Tejido blando (ICRU 44)", "1.06", "H, C, N, O, Na, P, S, Cl, K", "9"],
    ]
    tabla(["Material", "Nombre", "Rho", "Elementos", "#ZAIDs"], comp_rows)

    print(c("\n  → Fracciones negativas = fraccion de masa en MCNP", "green"))
    print(c("  → El tejido blando ICRU 44 se usa para TODOS los organos", "dim"))
    print(c("  → Material 1 (aire) solo en universo 1 (fondo)", "dim"))
    print(c("  → Material 2 (tejido) en universos 30, 50, 80, 90, 100", "dim"))
    return {"step": 11}


def step_12_footer(data: dict) -> dict:
    """Paso 12: RAND, DBCN, PRINT, PRDMP, NPS."""
    separador("PASO 12: FOOTER (RAND / NPS)", "─")
    caja("El footer del archivo contiene parametros de control:\n"
         "generador de numeros aleatorios, impresion, y el numero\n"
         "total de historias (NPS) a simular.",
         "cyan")

    nps = data.get("n_particles", int(1e7))

    print(c("  Footer:", "yellow"))
    print(textwrap.dedent(f"""\\
    rand stride=1111152917 gen=2 seed= 19703486396335   ← Generador aleatorio
    dbcn 48j 1                                          ← Debug
    print -85 -86 -128                                  ← Suprimir salidas largas
    PRDMP J 1e4 -1 1 1e4                                ← Output cada 10k historias
    NPS {nps}                                            ← Total de particulas
    """))

    footer_table = [
        ["rand stride=... gen=2 seed=N", "Generador numeros aleatorios LCG"],
        ["dbcn 48j 1", "Debug/checkpoint binario"],
        ["print -85 -86 -128", "Omite listados largos en output"],
        ["PRDMP J 1e4 -1 1 1e4", "Dump de resultados cada 1e4 historias"],
        [f"NPS {nps}", f"Numero total de historias a simular"],
    ]
    tabla(["Tarjeta", "Proposito"], footer_table)

    print(c(f"\n  → Con NPS = {nps:,}:", "green"))
    print(f"    Tiempo estimado: ~{max(1, nps // 500000)} min (aprox)")
    print(c(f"  → La seed se genera aleatoriamente cada vez", "dim"))
    print(c(f"  → Se pueden retomar simulaciones con la misma seed", "dim"))
    return {"step": 12}


# ═══════════════════════════════════════════════════════════════════════════
# ORQUESTADOR DEL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

STEPS = {
    1: step_1_volumen_ct,
    2: step_2_phantom_labelmap,
    3: step_3_pet_array,
    4: step_4_header,
    5: step_5_universos,
    6: step_6_lattice_rle,
    7: step_7_surfaces,
    8: step_8_mode,
    9: step_9_source,
    10: step_10_tallies,
    11: step_11_materials,
    12: step_12_footer,
}


def parse_rango(rango: str) -> list:
    """Parsea '1-5,7,9-12' → [1,2,3,4,5,7,9,10,11,12]."""
    steps = []
    for part in rango.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            steps.extend(range(int(a), int(b) + 1))
        else:
            steps.append(int(part))
    return sorted(set(s for s in steps if 1 <= s <= 12))


def generar_sintetico() -> dict:
    """Genera datos sinteticos para el pipeline."""
    nx, ny, nz = 64, 64, 32
    sx, sy, sz = 3.0, 3.0, 3.0
    return {
        "dims": (nx, ny, nz),
        "spacing": (sx, sy, sz),
        "has_pet": True,
        "isotope": "Y-90",
        "n_particles": int(1e7),
        "flip_rows": False,
    }


def analizar_archivo_i(path: str) -> dict:
    """Analiza un archivo .i existente y extrae metadata."""
    data = generar_sintetico()

    if not os.path.exists(path):
        print(c(f"  ⚠ Archivo no encontrado: {path}", "yellow"))
        print(c("  Usando datos sinteticos...", "dim"))
        return data

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Extraer isotopo del nombre o contenido
    iso_match = re.search(r"Y-90|I-131|Lu-177|Tc-99m", content)
    if iso_match:
        data["isotope"] = iso_match.group(0)

    # Extraer dimensiones del lattice
    fill_match = re.search(r"fill=(\d+):(\d+)\s+(\d+):(\d+)\s+(\d+):(\d+)", content)
    if fill_match:
        data["dims"] = (
            int(fill_match.group(2)) + 1,
            int(fill_match.group(4)) + 1,
            int(fill_match.group(6)) + 1,
        )

    # Extraer NPS
    nps_match = re.search(r"NPS\s+([\deE+\-\.]+)", content)
    if nps_match:
        val = nps_match.group(1)
        data["n_particles"] = int(float(val))

    # Extraer spacing de la superficie RPP
    rpp_match = re.search(r"1\s+rpp\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)", content)
    if rpp_match and data["dims"]:
        nx, ny, nz = data["dims"]
        xm = float(rpp_match.group(2))
        ym = float(rpp_match.group(4))
        zm = float(rpp_match.group(6))
        data["spacing"] = (xm / nx * 10, ym / ny * 10, zm / nz * 10)
        # redondear
        data["spacing"] = tuple(round(s, 2) for s in data["spacing"])

    return data


def run_ruflo_tracking(paso: int, state: dict) -> None:
    """Guarda el estado del pipeline en ruflo memory."""
    try:
        key = f"mcnp_pipeline_step_{paso}"
        val = json.dumps({"step": paso, "timestamp": datetime.now().isoformat(), "state": state})
        subprocess.run(
            ["npx", "--yes", "ruflo@latest", "memory", "store", "-k", key, "--value", val],
            capture_output=True, timeout=30, cwd=os.path.dirname(__file__)
        )
    except Exception as e:
        print(c(f"  ⚠ ruflo memory store fallo: {e}", "dim"))


def mostrar_resumen_final(data: dict) -> None:
    """Muestra resumen final de todo el pipeline."""
    separador("PIPELINE COMPLETO", "═")
    dims = data.get("dims", (64, 64, 32))
    spacing = data.get("spacing", (3.0, 3.0, 3.0))
    nx, ny, nz = dims
    total_voxels = nx * ny * nz
    total_mb = round(total_voxels * 4 / 1024 / 1024, 1)  # 4 bytes por int + overhead

    print(c(f"\n  📊 RESUMEN DE GENERACION MCNP", "bold"))
    print(f"\n  {'='*50}")

    summary = [
        ["Isotopo", data.get("isotope", "Y-90")],
        ["Particulas (NPS)", f"{data.get('n_particles', 1e7):.0e}"],
        ["Dimensiones (vox)", f"{nx} × {ny} × {nz}"],
        ["Voxeles totales", f"{total_voxels:,}"],
        ["Espaciado (mm)", f"{spacing}"],
        ["Tamano (cm)", f"{nx*spacing[0]/10:.1f} × {ny*spacing[1]/10:.1f} × {nz*spacing[2]/10:.1f}"],
        ["PET disponible", "Si" if data.get("has_pet") else "No"],
        ["Tamano archivo .i", f"~{total_mb} MB (estimado)"],
        ["Universos", "1 (aire), 30/50/80/90/100 (tejidos)"],
        ["Materiales", "m1 (aire), m2 (tejido ICRU 44)"],
        ["Tally", "TMESH F6 (MeV/g)"],
        ["Fuente", "Voxelizada via si5/sp5 + Y90cel3D.src"],
    ]
    tabla(["Parametro", "Valor"], summary)

    print(c(f"\n  {'✓' * 3} Pipeline visual completado {'✓' * 3}", "green"))
    print(c(f"\n  Para generar el MCNP real en Slicer:", "cyan"))
    print(c(f"    python run_mcnp.py --isotope {data.get('isotope', 'Y-90')} --n-particles {data.get('n_particles', 1e7):.0e}", "bold"))

    print(c(f"\n  O desde el pipeline completo:", "dim"))
    print(c(f"    Slicer.exe --python-script main.py --data-dir ... --segmenter simple", "dim"))


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline visual de generacion de input MCNP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Ejemplos:
              python mcnp_visual_pipeline.py
              python mcnp_visual_pipeline.py --file ../ej_mcnp/3Dosim_MCNP_Y90_universos.i
              python mcnp_visual_pipeline.py --synthetic --steps 5-7
              python mcnp_visual_pipeline.py --ruflo --steps 1-12
        """),
    )
    parser.add_argument("--file", type=str, default=None,
                        help="Ruta a archivo .i existente para analizar")
    parser.add_argument("--synthetic", action="store_true",
                        help="Usar datos sinteticos (64x64x32, 3mm)")
    parser.add_argument("--steps", type=str, default="1-12",
                        help="Rango de pasos, ej: '1-5' o '1,3,5-7'")
    parser.add_argument("--ruflo", action="store_true",
                        help="Habilitar tracking con ruflo memory")
    args = parser.parse_args()

    # Determinar fuente de datos
    if args.file:
        data = analizar_archivo_i(args.file)
        print(c(f"\n  Analizando archivo: {args.file}", "bold"))
    elif args.synthetic:
        data = generar_sintetico()
        print(c(f"\n  Usando datos sinteticos (64×64×32, 3mm)", "bold"))
    else:
        # Auto-detectar: buscar archivo ejemplo
        if os.path.exists(EXAMPLE_FILE):
            data = analizar_archivo_i(EXAMPLE_FILE)
            print(c(f"\n  Analizando archivo: {EXAMPLE_FILE}", "bold"))
        else:
            data = generar_sintetico()
            print(c(f"\n  Archivo ejemplo no encontrado, usando datos sinteticos", "dim"))

    # Determinar pasos
    steps_to_run = parse_rango(args.steps)
    total_steps = len(steps_to_run)

    separador()
    caja(f"PIPELINE VISUAL MCNP - {data.get('isotope', 'Y-90')}\n"
         f"{progreso(0, total_steps)}\n"
         f"Pasos a ejecutar: {args.steps}",
         "magenta")
    print(f"\n  {c('Este pipeline explica', 'dim')} COMO se genera un archivo de entrada MCNP")
    print(f"  {c('a partir de segmentacion CT/PET en 3Dosim.', 'dim')}")
    print()

    # Inicializar ruflo tracking si se pidio
    if args.ruflo:
        print(c(f"  ↳ ruflo memory tracking: ACTIVADO", "green"))
        run_ruflo_tracking(0, {"status": "started", "total_steps": total_steps})

    # Ejecutar cada paso
    for i, paso_num in enumerate(steps_to_run, 1):
        if paso_num in STEPS:
            print()
            print(c(f"  {progreso(i, total_steps)}", "bold"))
            state = STEPS[paso_num](data)
            if args.ruflo and state:
                run_ruflo_tracking(paso_num, state)
        else:
            print(c(f"\n  ⚠ Paso {paso_num} no valido", "red"))

    # Resumen final
    mostrar_resumen_final(data)

    # Final ruflo tracking
    if args.ruflo:
        run_ruflo_tracking(99, {"status": "completed"})
        print(c(f"\n  ↳ Estado final guardado en ruflo memory", "green"))

    separador()
    print(c("\n  FIN del pipeline visual MCNP", "bold"))
    print(c("  Ahora sabes como se genera cada parte del archivo .i\n", "dim"))


if __name__ == "__main__":
    main()
