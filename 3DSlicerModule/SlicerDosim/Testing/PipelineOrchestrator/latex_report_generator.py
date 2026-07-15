"""
latex_report_generator.py — Genera reporte LaTeX compilado desde Python.

Pipeline:
    datos Python (dicts / dataclasses)
    → figuras PNG (matplotlib)
    → template .tex.j2 (Jinja2)
    → compilación PDF (latexmk -xelatex)

Uso:
    from PipelineOrchestrator.latex_report_generator import generate_latex_report
    pdf_path = generate_latex_report(results_data, output_dir, patient_id="4090159")
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

import jinja2

logger = logging.getLogger("3DosimLaTeX")

# Constantes físicas (mismas que run_dosimetry_from_scene.py)
Y90_HALF_LIFE_H = 64.1
LAMDA_DECAY = np.log(2) / Y90_HALF_LIFE_H
MU_REPAIR = 0.28
MEV2J = 1.6e-13
ALPHA_BETA_LIVER = 2.5
ALPHA_BETA_TUMOR = 10
DENSIDAD_LIVER = 1.06
DENSIDAD_TUMOR = 1.06
DENSIDAD_PRETUMOR = 1.06
DENSIDAD_BODY = 1.0
DENSIDAD_AIR = 0.001
TAU_SECONDS = int(Y90_HALF_LIFE_H * 3600 / np.log(2))

# ── Config Jinja2 con delimitadores LaTeX-safe ──────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_FIGURES_DIR = Path(__file__).parent / "figures"

_JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,
)


# ── Filtros Jinja2 ─────────────────────────────────────────────────


def latex_escape(s: str) -> str:
    """Escapa caracteres especiales LaTeX en strings."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    result = []
    for c in str(s):
        result.append(replacements.get(c, c))
    return "".join(result)


def _fmt_commas(value) -> str:
    """Formatea número con separador de miles."""
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return str(value)


def _fmt1(value) -> str:
    """1 decimal."""
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _fmt2(value) -> str:
    """2 decimales."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)


def _fmt3(value) -> str:
    """3 decimales."""
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return str(value)


def _fmt4(value) -> str:
    """4 decimales."""
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def _fmt2e(value) -> str:
    """Notación científica, 2 decimales."""
    if isinstance(value, (int, float)):
        return f"{value:.2e}"
    return str(value)


_JINJA_ENV.filters["latex"] = latex_escape
_JINJA_ENV.filters["commas"] = _fmt_commas
_JINJA_ENV.filters["fmt1"] = _fmt1
_JINJA_ENV.filters["fmt2"] = _fmt2
_JINJA_ENV.filters["fmt3"] = _fmt3
_JINJA_ENV.filters["fmt4"] = _fmt4
_JINJA_ENV.filters["fmt2e"] = _fmt2e


# ── Funciones públicas ─────────────────────────────────────────────


def generate_latex_report(
    results_data: dict,
    output_dir: str,
    patient_id: str = "",
    dvh_curves: list = None,
) -> Optional[str]:
    """
    Genera reporte LaTeX compilado desde resultados dosimétricos.

    Args:
        results_data: dict con metadata, structures, mird
        output_dir: donde crear latex_report/ y el PDF final
        patient_id: ID del paciente para la portada
        dvh_curves: list of (name, d_vals_array, a_vals_array)

    Returns:
        ruta al PDF generado, o None si falla
    """
    output_dir = os.path.normpath(output_dir)
    latex_dir = os.path.normpath(os.path.join(output_dir, "latex_report"))
    figures_dir = os.path.join(latex_dir, "figures")
    out_dir = os.path.normpath(os.path.join(latex_dir, "out"))
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    meta = results_data.get("metadata", {})
    structures = results_data.get("structures", {})
    mird_data = results_data.get("mird", {})

    # ── Preparar datos para el template ──────────────────────────
    scene_name = meta.get("scene", "").replace("\\", "/").split("/")[-1]
    mctal_name = meta.get("mctal", "").replace("\\", "/").split("/")[-1]
    activity_gbq = float(meta.get("activity_gbq", 0))
    nps_val = int(meta.get("nps", 0))
    dims = meta.get("dimensions", [])
    flip_val = bool(meta.get("flip", True))
    gen_date = time.strftime("%Y-%m-%d %H:%M")

    # Estructuras ordenadas
    struct_order = ["higado", "tumor", "pretumor"]
    struct_labels = {"higado": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}

    structure_list = []
    has_structures = False
    has_biophysical = False
    for key in struct_order:
        s = structures.get(key, {})
        nv = s.get("n_voxels", 0)
        if nv == 0:
            continue
        has_structures = True
        bed_val = s.get("bed_gy", 0) or 0
        if bed_val > 0:
            has_biophysical = True
        structure_list.append({
            "key": key,
            "label": struct_labels.get(key, key),
            "n_voxels": nv,
            "volume_cm3": s.get("volume_cm3", 0),
            "mean_dose_gy": s.get("mean_dose_gy", 0),
            "d98_gy": s.get("d98_gy", 0),
            "d70_gy": s.get("d70_gy", 0),
            "d50_gy": s.get("d50_gy", 0),
            "d2_gy": s.get("max_dose_gy", 0),
            "bed_gy": bed_val,
            "eud_gy": s.get("eud_gy", 0) or 0,
            "eqd2_gy": s.get("eqd2_gy", 0) or 0,
        })

    # MIRD compartimentos
    mird_labels = {"liver": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}
    mird_list = []
    for key, label in mird_labels.items():
        c = mird_data.get(key, {})
        nv = c.get("n_voxels", 0)
        if nv > 0:
            mird_list.append({
                "label": label,
                "n_voxels": nv,
                "mean_dose_gy": c.get("mean_dose_gy", 0),
            })

    # Conclusiones
    tumor_dmax = structures.get("tumor", {}).get("max_dose_gy", 0) or 0
    tumor_dmean = structures.get("tumor", {}).get("mean_dose_gy", 0) or 0
    liver_dmean = structures.get("higado", {}).get("mean_dose_gy", 0) or 0
    ratio = tumor_dmean / liver_dmean if liver_dmean > 0 else 0

    # ── Generar figuras DVH ──────────────────────────────────────
    dvh_individual_files = _generate_dvh_figures(dvh_curves, figures_dir)
    dvh_combined_rel = _generate_dvh_combined(dvh_curves, figures_dir)

    # ── Renderizar template ──────────────────────────────────────
    template = _JINJA_ENV.get_template("reporte.tex.j2")

    template_data = {
        "patient_id": patient_id,
        "scene_name": scene_name if scene_name and scene_name != "N/A" else "",
        "mctal_name": mctal_name if mctal_name and mctal_name != "N/A" else "",
        "activity_gbq": activity_gbq,
        "nps": nps_val,
        "dim_x": dims[0] if dims and len(dims) >= 1 else 0,
        "dim_y": dims[1] if dims and len(dims) >= 2 else 0,
        "dim_z": dims[2] if dims and len(dims) >= 3 else 0,
        "flip": flip_val,
        "gen_date": gen_date,
        # Constantes
        "y90_half_life_h": Y90_HALF_LIFE_H,
        "lamda_decay": LAMDA_DECAY,
        "mu_repair": MU_REPAIR,
        "tau_seconds": TAU_SECONDS,
        "mev2j": MEV2J,
        # Tablas
        "alpha_beta_rows": [
            {"label": "Hígado", "value": ALPHA_BETA_LIVER, "type": "Tejido normal"},
            {"label": "Tumor", "value": ALPHA_BETA_TUMOR, "type": "Tumor maligno"},
            {"label": "Peritumoral", "value": ALPHA_BETA_LIVER, "type": "Tejido normal"},
        ],
        "density_rows": [
            {"material": "Hígado / Tumor / Peritumoral", "density": DENSIDAD_LIVER, "use": "Tejido hepático"},
            {"material": "Body (default)", "density": DENSIDAD_BODY, "use": "Contorno corporal"},
            {"material": "Aire", "density": DENSIDAD_AIR, "use": "Exterior"},
        ],
        # Estructuras
        "structure_list": structure_list,
        "has_structures": has_structures,
        "has_biophysical": has_biophysical,
        # MIRD
        "mird_list": mird_list,
        "mird_activity_gbq": activity_gbq,
        # DVH
        "has_dvh": dvh_combined_rel is not None or len(dvh_individual_files) > 0,
        "dvh_combined_rel": "figures/dvh_combined.png" if dvh_combined_rel else None,
        "dvh_individual_files": dvh_individual_files,
        # Conclusiones
        "tumor_dmax": tumor_dmax,
        "tumor_dmean": tumor_dmean,
        "liver_dmean": liver_dmean,
        "ratio": ratio,
    }

    tex_content = template.render(**template_data)

    tex_path = os.path.join(latex_dir, "main.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    logger.info(f"  Template renderizado: {tex_path}")

    # ── compile.bat (fallback manual) ────────────────────────────
    _write_compile_bat(latex_dir)

    # ── Compilar ─────────────────────────────────────────────────
    pdf_path = _compile_latex(latex_dir)

    # ── Copiar PDF final ─────────────────────────────────────────
    if pdf_path and os.path.exists(pdf_path):
        final_pdf = os.path.join(output_dir, "dosimetria_report_latex.pdf")
        try:
            shutil.copy2(pdf_path, final_pdf)
            logger.info(f"  Reporte LaTeX copiado a: {final_pdf}")
            return final_pdf
        except Exception as e:
            logger.warning(f"  No se pudo copiar PDF: {e}")
            return pdf_path

    return None


# ── Figuras DVH ────────────────────────────────────────────────────


def _generate_dvh_figures(
    dvh_curves: list,
    figures_dir: str,
) -> list:
    """Genera figuras DVH individuales. Retorna lista de nombres de archivo."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    result_files = []
    colors = {"Hígado": "#2563EB", "Tumor": "#DC2626", "Peritumoral": "#D97706"}

    if not dvh_curves:
        return result_files

    for name, d_vals, a_vals in dvh_curves:
        safe_name = name.replace("í", "i").replace("ó", "o").replace(" ", "_").lower()
        filepath = os.path.join(figures_dir, f"dvh_{safe_name}.png")
        color = colors.get(name, "#1B2A4A")

        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")
        ax.plot(d_vals, a_vals, color=color, linewidth=2, label=name)
        ax.set_xlabel("Dosis (Gy)", fontsize=11)
        ax.set_ylabel("Volumen (%)", fontsize=11)
        ax.set_title(f"DVH - {name}", fontsize=13, fontweight="bold")
        ax.set_yscale("log")
        ax.set_ylim(0.1, 110)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        fig.tight_layout()
        fig.savefig(filepath, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        result_files.append(os.path.basename(filepath))
        logger.info(f"  DVH figure: {filepath}")

    return result_files


def _generate_dvh_combined(
    dvh_curves: list,
    figures_dir: str,
) -> Optional[str]:
    """Genera figura DVH combinada. Retorna ruta relativa o None."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not dvh_curves:
        return None

    colors = {"Hígado": "#2563EB", "Tumor": "#DC2626", "Peritumoral": "#D97706"}

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")
    for name, d_vals, a_vals in dvh_curves:
        color = colors.get(name, "#1B2A4A")
        ax.plot(d_vals, a_vals, color=color, linewidth=2, label=name)

    ax.set_xlabel("Dosis (Gy)", fontsize=12)
    ax.set_ylabel("Volumen (%)", fontsize=12)
    ax.set_title("DVH Combinado - Todas las Estructuras", fontsize=14, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 110)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc="best")
    fig.tight_layout()

    filepath = os.path.join(figures_dir, "dvh_combined.png")
    fig.savefig(filepath, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"  DVH combined: {filepath}")
    return "figures/dvh_combined.png"


# ── Compilación ────────────────────────────────────────────────────


def _write_compile_bat(latex_dir: str):
    """Escribe compile.bat para compilación manual (fallback)."""
    bat_content = r"""@echo off
REM Compilar reporte LaTeX con latexmk -xelatex (o xelatex directo)
echo Compilando reporte LaTeX...
echo.
set DIR=%~dp0

REM Intentar con latexmk (gestiona pasadas automaticamente)
where latexmk >nul 2>nul
if %ERRORLEVEL%==0 (
    latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=%DIR%out %DIR%main.tex
) else (
    REM Fallback: xelatex directo (2 pasadas)
    xelatex -interaction=nonstopmode -output-directory=%DIR%out %DIR%main.tex
    xelatex -interaction=nonstopmode -output-directory=%DIR%out %DIR%main.tex
)
echo.
if exist "%DIR%out\main.pdf" (
    echo PDF generado: %DIR%out\main.pdf
    copy /Y "%DIR%out\main.pdf" "%DIR%..\dosimetria_report_latex.pdf" >nul
    echo Copiado a: %DIR%..\dosimetria_report_latex.pdf
) else (
    echo ERROR: No se pudo generar el PDF.
    echo Revise %DIR%out\main.log
)
pause
"""
    bat_path = os.path.join(latex_dir, "compile.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    logger.info(f"  compile.bat escrito: {bat_path}")


def _compile_latex(latex_dir: str) -> Optional[str]:
    """Compila main.tex con latexmk -xelatex. Fallback a xelatex directo."""
    latex_dir = os.path.normpath(latex_dir)
    main_tex = os.path.normpath(os.path.join(latex_dir, "main.tex"))
    out_dir = os.path.normpath(os.path.join(latex_dir, "out"))

    if not os.path.exists(main_tex):
        logger.error(f"  main.tex no encontrado: {main_tex}")
        return None

    # Asegurar que figures/ está accesible para LaTeX
    figures_src = os.path.join(latex_dir, "figures")
    figures_dst = os.path.join(out_dir, "figures")
    if os.path.exists(figures_dst):
        shutil.rmtree(figures_dst)
    if os.path.exists(figures_src):
        shutil.copytree(figures_src, figures_dst)

    # 1. Intentar latexmk
    latexmk_path = shutil.which("latexmk")
    if latexmk_path:
        logger.info("  Compilando con latexmk -xelatex...")
        try:
            result = subprocess.run(
                [latexmk_path, "-xelatex",
                 "-interaction=nonstopmode",
                 "-halt-on-error",
                 f"-outdir={out_dir}",
                 str(main_tex)],
                cwd=latex_dir,
                timeout=180,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                pdf_path = os.path.join(out_dir, "main.pdf")
                if os.path.exists(pdf_path):
                    size_kb = os.path.getsize(pdf_path) / 1024
                    logger.info(f"  PDF compilado: {pdf_path} ({size_kb:.0f} KB)")
                    return pdf_path
            else:
                # latexmk falló, mostrar diagnóstico
                stderr_lines = result.stderr.split("\n")
                errors = [l for l in stderr_lines if "Error" in l or "Fatal" in l or "!" in l]
                if errors:
                    for e in errors[:5]:
                        logger.warning(f"    {e.strip()}")
                logger.warning("  latexmk falló, intentando xelatex directo...")
        except subprocess.TimeoutExpired:
            logger.warning("  latexmk excedió timeout, intentando xelatex directo...")
        except Exception as e:
            logger.warning(f"  latexmk error: {e}, intentando xelatex directo...")
    else:
        logger.info("  latexmk no disponible. Usando xelatex directo (2 pasadas)...")

    # 2. Fallback: xelatex directo (2 pasadas)
    xelatex_path = shutil.which("xelatex")
    if not xelatex_path:
        candidates = [
            r"C:\Users\Sebastian\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe",
            r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                xelatex_path = c
                break

    if not xelatex_path:
        logger.error("  xelatex no disponible. El PDF no se compilará.")
        return None

    for i in range(2):
        logger.info(f"  Pasada {i+1}/2 de xelatex...")
        try:
            result = subprocess.run(
                [xelatex_path, "-interaction=nonstopmode",
                 "-output-directory", out_dir, main_tex],
                cwd=latex_dir,
                timeout=120,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors = [l for l in result.stderr.split("\n")
                         if "Error" in l or "Fatal" in l]
                if errors:
                    for e in errors[:5]:
                        logger.warning(f"    LaTeX: {e.strip()}")
        except subprocess.TimeoutExpired:
            logger.warning(f"  xelatex paso {i+1} excedió timeout")
        except Exception as e:
            logger.error(f"  Error ejecutando xelatex: {e}")
            return None

    pdf_path = os.path.join(out_dir, "main.pdf")
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        logger.info(f"  PDF compilado: {pdf_path} ({size_kb:.0f} KB)")
        return pdf_path

    logger.error(f"  PDF no generado. Revise {os.path.join(out_dir, 'main.log')}")
    return None


# ── Demo sintético ─────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generar reporte LaTeX desde JSON o demo")
    parser.add_argument("--json", help="Ruta a dosimetria_report.json")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--patient-id", default="", help="ID del paciente")
    parser.add_argument("--demo", action="store_true", help="Ejecutar con datos sintéticos")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.demo:
        # ── Datos sintéticos de demostración ────────────────────────
        logger.info("=" * 60)
        logger.info("  Demostración: Reporte LaTeX con datos sintéticos")
        logger.info("=" * 60)

        demo_data = {
            "metadata": {
                "scene": "3Dosim_scene.mrb",
                "mctal": "mctal_demo.m",
                "activity_bq": 3137000000.0,
                "activity_gbq": 3.137,
                "dimensions": [512, 512, 171],
                "nps": 100000000,
                "flip": True,
            },
            "structures": {
                "higado": {
                    "index": 90, "n_voxels": 950000, "volume_cm3": 1250.0,
                    "mean_dose_gy": 25.3, "min_dose_gy": 0.1, "max_dose_gy": 85.2,
                    "std_dose_gy": 15.1, "d98_gy": 2.1, "d70_gy": 15.2,
                    "d50_gy": 22.1, "bed_gy": 35.8, "eud_gy": 20.4, "eqd2_gy": 28.3,
                },
                "tumor": {
                    "index": 100, "n_voxels": 12000, "volume_cm3": 15.8,
                    "mean_dose_gy": 120.5, "min_dose_gy": 45.2, "max_dose_gy": 210.3,
                    "std_dose_gy": 30.2, "d98_gy": 55.2, "d70_gy": 95.2,
                    "d50_gy": 118.0, "bed_gy": 185.2, "eud_gy": 110.3, "eqd2_gy": 42.1,
                },
                "pretumor": {
                    "index": 200, "n_voxels": 45000, "volume_cm3": 59.2,
                    "mean_dose_gy": 18.7, "min_dose_gy": 0.5, "max_dose_gy": 55.2,
                    "std_dose_gy": 10.2, "d98_gy": 1.5, "d70_gy": 10.2,
                    "d50_gy": 16.5, "bed_gy": 25.3, "eud_gy": 15.2, "eqd2_gy": 20.4,
                },
            },
            "mird": {
                "activity_gbq": 3.137,
                "liver": {"n_voxels": 950000, "mean_dose_gy": 25.3},
                "tumor": {"n_voxels": 12000, "mean_dose_gy": 120.5},
                "pretumor": {"n_voxels": 45000, "mean_dose_gy": 18.7},
            },
        }

        demo_dvh = [
            ("Hígado", [0, 10, 20, 30, 40, 50], [100, 85, 60, 35, 15, 5]),
            ("Tumor", [0, 50, 100, 150, 200], [100, 90, 60, 25, 5]),
            ("Peritumoral", [0, 10, 20, 30, 40, 50], [100, 88, 65, 40, 20, 8]),
        ]

        out_dir = args.output or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
            "resultados_test", "latex_demo"
        )

        pdf = generate_latex_report(
            demo_data, out_dir,
            patient_id=args.patient_id or "DEMO-001",
            dvh_curves=demo_dvh,
        )

        if pdf:
            logger.info(f"\n  ✅ PDF generado: {pdf}")
            logger.info(f"  Tamaño: {os.path.getsize(pdf) / 1024:.0f} KB")
        else:
            logger.error("\n  ❌ No se pudo generar el PDF")
        sys.exit(0)

    if args.json:
        with open(args.json, "r") as f:
            import json
            data = json.load(f)
        out_dir = args.output or os.path.dirname(os.path.abspath(args.json))
        pdf = generate_latex_report(data, out_dir, patient_id=args.patient_id)
        if pdf:
            print(f"\nReporte LaTeX generado: {pdf}")
        else:
            print("\nERROR: No se pudo generar el reporte LaTeX")
            sys.exit(1)
    else:
        parser.print_help()
