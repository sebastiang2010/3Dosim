"""
run_dosimetry_from_scene.py — Pipeline de dosimetria desde escena existente.

Carga una escena .mrb (con CT, PET, 3Dosim_labelmap), parsea un archivo
MCTAL (FMESH4 tally 1), computa dosis en Gy y reporta resultados por
estructura (higado=90, tumor=100, pretumor=99).

Uso:
  Slicer.exe --python-script run_dosimetry_from_scene.py ^
      --scene "C:/MAT/3Dosim/ai-pipe/scenes/3Dosim_scene.mrb" ^
      --mctal "C:/MAT/3Dosim/corrida-Manu/mctal/mctal.m"

Sin argumentos busca automaticamente:
  - Escena: C:\MAT\3Dosim\ai-pipe\scenes\3Dosim_scene.mrb
  - MCTAL:  C:\MAT\3Dosim\corrida-Manu\mctal\mctal.m
  - Actividad: se computa del PET en la escena

Requiere:
  - 3D Slicer (slicer, vtk accesibles en Python)
  - SlicerDosimLib en el path

Algoritmo:
  1. Carga escena .mrb en Slicer
  2. Busca nodos: CT, PET, 3Dosim_labelmap
  3. Computa actividad total del PET
  4. Parsea MCTAL con MCTALParser (compatible MATLAB f_cargo_mctall.m)
  5. Convierte MeV/cm³/particula → Gy (MATLAB cargo_mctal.m:389-395)
  6. Por estructura: DVH, D98/D70/D50, BED, EUD, EQD2
  7. Reporte JSON + visualizacion en Slicer
"""

from __future__ import annotations

import argparse
import json
import logging
import numpy as np
import os
import sys
import time
from typing import Optional

# ======================================================================
# DEBUG: primer output inmediato
# ======================================================================
_debug_file = r"C:\MAT\3Dosim\ai-pipe\resultados_dosimetria\_debug_start.log"
try:
    os.makedirs(r"C:\MAT\3Dosim\ai-pipe\resultados_dosimetria", exist_ok=True)
    with open(_debug_file, "w") as _df:
        _df.write(f"SCRIPT STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        _df.write(f"sys.argv: {sys.argv}\n")
        _df.write(f"Python: {sys.version}\n")
        _df.write(f"slicer in sys.modules: {'slicer' in sys.modules}\n")
except Exception as _e:
    pass

# ======================================================================
# Paths
# ======================================================================

SCENE_DEFAULT = r"C:\MAT\3Dosim\ai-pipe\scenes\3Dosim_scene.mrb"
MCTAL_DEFAULT = r"C:\MAT\3Dosim\corrida-Manu\mctal\mctal.m"
OUTPUT_DIR_DEFAULT = r"C:\MAT\3Dosim\ai-pipe\resultados_dosimetria"
LABELMAP_DEFAULT = r"C:\MAT\3Dosim\ai-pipe\3Dosim_labelmap.nii"

# Indices de tejido en el labelmap (universe numbers de MCNP)
LIVER_INDEX = 90
TUMOR_INDEX = 100
PRETUMOR_INDEX = 99
AIR_INDEX = 0

# Densidades (g/cm³) — MATLAB cargo_mctal.m
DENSIDAD_LIVER = 1.06  # g/cm³
DENSIDAD_TUMOR = 1.06
DENSIDAD_PRETUMOR = 1.06
DENSIDAD_BODY = 1.0
DENSIDAD_AIR = 0.001

# Parametros radiobiologicos — MATLAB cargo_mctal.m lineas 278-288
ALPHA_BETA_LIVER = 2.5  # Gy
ALPHA_BETA_TUMOR = 10  # Gy
MU_REPAIR = 0.28  # h^-1 (T_repair = 2.5 h)
Y90_HALF_LIFE_H = 64.1  # h
LAMDA_DECAY = np.log(2) / Y90_HALF_LIFE_H  # h^-1

# Conversion
MEV2J = 1.6e-13

# Logger simple con archivo directo y stdout
_log_path = os.path.join(OUTPUT_DIR_DEFAULT, "dosimetria_pipeline.log")
_log_file = None
try:
    os.makedirs(OUTPUT_DIR_DEFAULT, exist_ok=True)
    _log_file = open(_log_path, "w", encoding="utf-8")
except Exception:
    pass


# Reemplazar logger con funcion que escribe a stderr + archivo
class _Logger:
    """Logger que escribe a stderr (visible en shell) y archivo."""
    @staticmethod
    def info(msg): _log_msg("INFO", msg)
    @staticmethod
    def warning(msg): _log_msg("WARN", msg)
    @staticmethod
    def error(msg): _log_msg("ERROR", msg)
    @staticmethod
    def debug(msg): pass

def _log_msg(level, msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    if _log_file:
        try:
            _log_file.write(line + "\n")
            _log_file.flush()
        except Exception:
            pass

logger = _Logger()
# Alias corto
log = logger.info


# ======================================================================
# 1. Scene loading
# ======================================================================

def load_scene(scene_path: str) -> bool:
    """Carga escena .mrb en Slicer."""
    import slicer

    if not os.path.exists(scene_path):
        logger.error(f"Escena no encontrada: {scene_path}")
        return False

    logger.info(f"Cargando escena: {scene_path}")
    logger.info(f"  Tamano: {os.path.getsize(scene_path) / 1024 / 1024:.1f} MB")

    success = slicer.util.loadScene(scene_path)
    if not success:
        logger.error("Error cargando escena")
        return False

    logger.info("Escena cargada correctamente")
    return True


def find_nodes(labelmap_name: str = "3Dosim_labelmap") -> dict:
    """
    Busca nodos en la escena: CT, PET, labelmap.

    Returns:
        dict con 'ct', 'pet', 'labelmap' (nodos Slicer) o None
    """
    import slicer

    nodes = {"ct": None, "pet": None, "labelmap": None}

    # Buscar todos los volumenes
    all_volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

    for vol in all_volumes:
        name = vol.GetName()
        name_lower = name.lower()

        if "labelmap" in name_lower or "phantom" in name_lower:
            if labelmap_name in name:
                nodes["labelmap"] = vol
                logger.info(f"  Labelmap: {name}")
        elif "ct" in name_lower or "ct_" in name_lower:
            nodes["ct"] = vol
            logger.info(f"  CT: {name}")
        elif "pet" in name_lower:
            nodes["pet"] = vol
            logger.info(f"  PET: {name}")

    # Si no encontro por nombre, buscar por tipo/indice
    if nodes["ct"] is None:
        for vol in all_volumes:
            name = vol.GetName()
            if "ct" in name.lower():
                nodes["ct"] = vol
                break

    if nodes["pet"] is None:
        for vol in all_volumes:
            name = vol.GetName()
            if "pet" in name.lower() or "pt_" in name.lower():
                nodes["pet"] = vol
                break

    # Buscar segmentacion como fallback para labelmap
    if nodes["labelmap"] is None:
        seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if seg_nodes:
            nodes["segmentation"] = seg_nodes[0]
            logger.info(f"  Segmentacion: {seg_nodes[0].GetName()} (fallback)")

    return nodes


def compute_activity_from_pet(pet_node) -> float:
    """
    Computa actividad total desde nodo PET.

    PET puede venir en Bq/ml o Bq.
    Si es Bq/ml: multiplica por volumen de voxel.
    Si es Bq: suma directa.

    Returns:
        actividad total en Bq
    """
    import slicer

    pet_array = slicer.util.arrayFromVolume(pet_node)  # (nz, ny, nx)
    spacing = pet_node.GetSpacing()  # (sx, sy, sz) mm

    # Volumen de voxel en ml (= cm³)
    voxel_vol_ml = (spacing[0] / 10) * (spacing[1] / 10) * (spacing[2] / 10)
    # mm³ → cm³ = ml, dividir por 1000
    voxel_vol_ml = (spacing[0] * spacing[1] * spacing[2]) / 1000.0

    # Sumar PET
    total_pet = np.sum(pet_array)

    # Verificar si son valores pequenos (Bq/ml) o grandes (Bq)
    # Tipicamente Bq/ml son valores tipo 1e4-1e7, Bq son 1e9-1e10
    if total_pet < 1e8:
        # Parece Bq/ml, multiplicar por volumen
        activity_bq = total_pet * voxel_vol_ml
        logger.info(f"  PET en Bq/ml: sum={total_pet:.2e}, vol_voxel={voxel_vol_ml:.6f} ml")
    else:
        # Parece Bq directos
        activity_bq = total_pet
        logger.info(f"  PET en Bq: sum={total_pet:.2e}")

    logger.info(f"  Actividad total: {activity_bq:.2e} Bq = {activity_bq / 1e9:.4f} GBq")
    return float(activity_bq)


# ======================================================================
# 2. MCTAL Parser (wrapper)
# ======================================================================

def parse_mctal(mctal_path: str, dims: tuple) -> dict:
    """Parsea MCTAL usando SlicerDosimLib MCTALParser."""
    # Agregar SlicerDosimLib al path
    lib_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "Modules",
        "Scripted", "SlicerDosim", "SlicerDosimLib",
    )
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)

    from mctal_parser import MCTALParser

    parser = MCTALParser()
    nx, ny, nz = dims
    result = parser.parse(mctal_path, nx=nx, ny=ny, nz=nz)

    if result["dose_3d"] is None:
        raise RuntimeError("No se pudo extraer dosis 3D del MCTAL")

    logger.info(
        f"MCTAL parseado: {result['dimensions']}, "
        f"NPS={result['nps']}, "
        f"title={result['title'][:60]}"
    )

    return result


# ======================================================================
# 3. Conversion a Gy
# ======================================================================

def convert_to_gy(
    dose_mev_cm3: np.ndarray,
    labelmap: np.ndarray,
    activity_bq: float,
    t_meanlife_s: float,
) -> np.ndarray:
    """
    Convierte MeV/cm³/particula → Gy.

    Algoritmo MATLAB cargo_mctal.m lineas 389-395:
      1. D / rho  (MeV/cm³ → MeV/g) usando densidad por tejido
      2. * MeV2J   (MeV/g → J/g)
      3. * t * Actividad (escalar por desintegraciones totales)
      4. * 1000   (J/g → J/kg = Gy)
    """
    # Densidades por indice de tejido
    cell_densities = {
        LIVER_INDEX: DENSIDAD_LIVER,
        TUMOR_INDEX: DENSIDAD_TUMOR,
        PRETUMOR_INDEX: DENSIDAD_PRETUMOR,
    }

    # Mapa de densidad del mismo shape que dosis
    dens_map = np.ones_like(dose_mev_cm3, dtype=np.float64)
    for idx, dens in cell_densities.items():
        mask = labelmap == idx
        dens_map[mask] = dens

    # Aire: densidad muy baja, marcar para evitar division por cero
    air_mask = labelmap == AIR_INDEX

    # Paso 1: MeV/cm³ → MeV/g dividiendo por densidad
    dose_mev_g = np.divide(
        dose_mev_cm3, dens_map,
        out=np.zeros_like(dose_mev_cm3),
        where=dens_map > 0.001,
    )

    # Paso 2: MeV/g → J/g
    dose_j_g = dose_mev_g * MEV2J

    # Paso 3: Escalar por desintegraciones totales
    # D_J/g total = D_J/g por particula * t_meanlife * Actividad_Bq
    dose_j_g_total = dose_j_g * t_meanlife_s * activity_bq

    # Paso 4: J/g → J/kg = Gy
    dose_gy = dose_j_g_total * 1000.0

    # Aire: dosis = 0
    dose_gy[air_mask] = 0.0

    return dose_gy


# ======================================================================
# 4. DVH y estadisticas por estructura
# ======================================================================

def compute_dvh(
    dose_gy: np.ndarray,
    labelmap: np.ndarray,
    structure_idx: int,
    bins: int = 200,
) -> dict:
    """
    Computa DVH para una estructura.

    Returns:
        dict con:
          - 'volume_ml': volumen de la estructura
          - 'mean_dose_gy': dosis media
          - 'min_dose_gy': dosis minima
          - 'max_dose_gy': dosis maxima
          - 'std_dose_gy': desviacion estandar
          - 'd98_gy': dosis al 98% del volumen
          - 'd70_gy': dosis al 70%
          - 'd50_gy': dosis al 50%
          - 'dose_bins': array de dosis para DVH
          - 'volume_hist': histograma de volumen vs dosis
          - 'cumulative_vol': histograma acumulativo
    """
    mask = labelmap == structure_idx
    n_voxels = np.sum(mask)

    if n_voxels == 0:
        logger.warning(f"Estructura {structure_idx}: sin voxeles")
        return {"volume_ml": 0, "mean_dose_gy": 0, "n_voxels": 0}

    doses = dose_gy[mask]
    n_total = len(doses)
    spacing = None  # lo necesitamos para volumen

    # Estadisticas basicas (todos los voxeles, incluyendo dosis=0)
    mean_dose = float(np.mean(doses))
    min_dose = float(np.min(doses))
    max_dose = float(np.max(doses))
    std_dose = float(np.std(doses))

    # Fraccion de voxeles con dosis > 0
    n_nonzero = int(np.sum(doses > 0))
    frac_zero = (n_total - n_nonzero) / n_total * 100

    # D98, D70, D50 — percentiles de dosis
    # Usar SOLO voxeles con dosis > 0 para percentiles clinicos
    # (voxeles con dosis=0 estan fuera del alcance de la fuente MCNP)
    doses_pos = doses[doses > 0]
    if len(doses_pos) > 0:
        d98 = float(np.percentile(doses_pos, max(2, 100 * (n_total - n_nonzero) / n_total + 2)))
        d70 = float(np.percentile(doses_pos, 30) if len(doses_pos) >= 10 else 0)
        d50 = float(np.percentile(doses_pos, 50) if len(doses_pos) >= 10 else 0)
    else:
        d98 = d70 = d50 = 0.0

    # DVH histograma
    dose_max_hist = float(np.percentile(doses, 99.5))  # evitar outliers
    if dose_max_hist <= 0:
        dose_max_hist = max_dose

    hist, edges = np.histogram(
        doses, bins=bins, range=(0, dose_max_hist * 1.05)
    )
    # hist: conteo de voxeles por bin
    # cumulative: fraccion de volumen que recibe ≥ dosis
    cumulative = np.cumsum(hist[::-1])[::-1]
    cumulative_vol = cumulative / n_voxels * 100  # porcentaje

    # Centros de bin para graficar
    dose_bins = (edges[:-1] + edges[1:]) / 2

    return {
        "structure_idx": int(structure_idx),
        "n_voxels": int(n_voxels),
        "mean_dose_gy": mean_dose,
        "min_dose_gy": min_dose,
        "max_dose_gy": max_dose,
        "std_dose_gy": std_dose,
        "d98_gy": d98,
        "d70_gy": d70,
        "d50_gy": d50,
        "dose_bins_gy": dose_bins.tolist(),
        "volume_hist_pct": (hist / n_voxels * 100).tolist(),
        "cumulative_vol_pct": cumulative_vol.tolist(),
    }


def compute_biophysical(
    dvh_result: dict,
    alpha_beta: float,
    is_tumor: bool = False,
) -> dict:
    """
    Computa BED, EUD, EQD2.

    BED = D + (lamda/((alpha/beta)*(lamda+mu))) * D²
    (MATLAB f_BED.m)

    EUD = sum(vi * Di^a)^(1/a) donde a=1 para tumor, a=-10 para normal
    EQD2 = BED / (1 + 2/(alpha/beta))

    Args:
        dvh_result: resultado de compute_dvh()
        alpha_beta: relacion alfa/beta (2.5 liver, 10 tumor)
        is_tumor: si es tumor (a=1) o normal (a=-10)

    Returns:
        dict con BED, EUD, EQD2
    """
    mean_d = dvh_result.get("mean_dose_gy", 0)
    if mean_d <= 0:
        return {"bed_gy": 0, "eud_gy": 0, "eqd2_gy": 0}

    # BED — MATLAB f_BED.m
    # BED = D + lambda/((alpha/beta)*(lambda+mu)) * D²
    # Donde lambda = ln(2)/T_half, mu = repair rate
    lamda = LAMDA_DECAY  # h^-1
    mu = MU_REPAIR  # h^-1

    bed_factor = lamda / (alpha_beta * (lamda + mu))
    bed = mean_d + bed_factor * mean_d**2

    # EUD — MATLAB f_EUD.m
    # EUD = (sum(vi * Di^a))^(1/a)
    # a = 1 para tumor, a = 1 - n para tejido normal (n=-10 para liver)
    if is_tumor:
        a = 1.0
    else:
        a = 1.0 - (-10.0)  # n = -10 → a = 11

    # Para simplificar, usar mean dose si no tenemos histograma completo
    if is_tumor:
        eud = mean_d
    else:
        # EUD para tejido normal: aproximacion con dosis media
        # (EUD exacto requiere histograma completo)
        eud = mean_d

    # EQD2 (2 Gy fractions)
    # EQD2 = D * (d + alpha/beta) / (2 + alpha/beta)
    # Para BED: EQD2 = BED / (1 + 2/(alpha/beta))
    eqd2 = bed / (1 + 2.0 / alpha_beta)

    return {
        "bed_gy": round(bed, 4),
        "eud_gy": round(eud, 4),
        "eqd2_gy": round(eqd2, 4),
        "alpha_beta": alpha_beta,
        "is_tumor": is_tumor,
    }


# ======================================================================
# 5. MIRD partition model
# ======================================================================

def compute_mird(
    dose_gy: np.ndarray,
    labelmap: np.ndarray,
    activity_gbq: float,
) -> dict:
    """
    Calcula MIRD partition model para higado y tumor.

    MATLAB cargo_mctal.m lineas 211-227.
    """
    # Volumenes
    voxel_vol = 1.0  # se ajusta despues
    n_liver = np.sum(labelmap == LIVER_INDEX)
    n_tumor = np.sum(labelmap == TUMOR_INDEX)
    n_pretumor = np.sum(labelmap == PRETUMOR_INDEX)

    # Dosis medias
    d_liver_mean = float(np.mean(dose_gy[labelmap == LIVER_INDEX])) if n_liver > 0 else 0
    d_tumor_mean = float(np.mean(dose_gy[labelmap == TUMOR_INDEX])) if n_tumor > 0 else 0
    d_pretumor_mean = float(np.mean(dose_gy[labelmap == PRETUMOR_INDEX])) if n_pretumor > 0 else 0

    # K constante MIRD
    k = 48.98  # J-s

    resultado = {
        "activity_gbq": activity_gbq,
        "liver": {
            "n_voxels": int(n_liver),
            "mean_dose_gy": round(d_liver_mean, 4),
        },
        "tumor": {
            "n_voxels": int(n_tumor),
            "mean_dose_gy": round(d_tumor_mean, 4),
        },
        "pretumor": {
            "n_voxels": int(n_pretumor),
            "mean_dose_gy": round(d_pretumor_mean, 4),
        },
        "k_mird": k,
    }

    return resultado


# ======================================================================
# 7. DVH plots en Slicer (algoritmo MATLAB f_HDV.m)
# ======================================================================

def _create_dvh_plots_slicer(dose_gy, labelmap, spacing, show_gui=True):
    """
    Crea graficos DVH acumulativos en Slicer usando algoritmo MATLAB f_HDV.m.

    MATLAB:
        Dmax = max(D);
        delta = Dmax / 1000;
        for d = 0:delta:Dmax
            a(i) = sum(D >= d) * 100 / n;
        end
        plot(d, a);  % escala Y log

    Crea un PlotChartNode con una serie por estructura.
    """
    import slicer
    import vtk

    structures = [
        ("Higado", LIVER_INDEX, (0.2, 0.4, 1.0)),     # azul
        ("Tumor", TUMOR_INDEX, (1.0, 0.2, 0.2)),       # rojo
        ("Pretumor", PRETUMOR_INDEX, (0.2, 1.0, 0.2)), # verde
    ]

    chart_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLPlotChartNode", "DVH_Chart"
    )
    chart_node.SetTitle("Cumulative Dose Volume Histogram")
    chart_node.SetXAxisTitle("Dose (Gy)")
    chart_node.SetYAxisTitle("Volume (%)")
    # Escala Y log — Slicer 5.8 usa SetYAxisLogScale(int)
    if hasattr(chart_node, "SetYAxisLogScale"):
        chart_node.SetYAxisLogScale(1)
    elif hasattr(chart_node, "SetYAxisLog"):
        chart_node.SetYAxisLog(True)

    series_nodes = []
    dvh_curves = []  # para exportar PNG

    for name, idx, color in structures:
        mask = labelmap == idx
        doses = dose_gy[mask]
        n = len(doses)

        if n == 0 or np.max(doses) <= 0:
            continue

        # --- Algoritmo MATLAB f_HDV.m exacto ---
        Dmax = float(np.max(doses))
        delta = Dmax / 1000.0
        d_vals = np.arange(0, Dmax + delta, delta)
        a_vals = np.zeros(len(d_vals))
        for i, d in enumerate(d_vals):
            a_vals[i] = np.sum(doses >= d) * 100.0 / n
        # ----------------------------------------

        # Crear tabla con datos DVH (API Slicer 5.8)
        table_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLTableNode", f"DVH_Table_{name}"
        )
        table = table_node.GetTable()
        col_x = vtk.vtkFloatArray()
        col_x.SetName("Dose (Gy)")
        col_y = vtk.vtkFloatArray()
        col_y.SetName("Volume (%)")
        for i in range(len(d_vals)):
            col_x.InsertNextValue(float(d_vals[i]))
            col_y.InsertNextValue(float(a_vals[i]))
        table.AddColumn(col_x)
        table.AddColumn(col_y)

        # Crear serie que referencia la tabla
        series = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLPlotSeriesNode", f"DVH_{name}"
        )
        series.SetAndObserveTableNodeID(table_node.GetID())
        series.SetXColumnName("Dose (Gy)")
        series.SetYColumnName("Volume (%)")
        series.SetPlotType(slicer.vtkMRMLPlotSeriesNode.PlotTypeLine)
        series.SetColor(*color)
        series.SetLineWidth(2)

        chart_node.AddAndObservePlotSeriesNodeID(series.GetID())
        series_nodes.append(series)
        dvh_curves.append((name, d_vals, a_vals))

        logger.info(f"  DVH creado: {name} ({n} voxels, Dmax={Dmax:.1f} Gy)")

    # Activar modulo Plots
    if series_nodes and show_gui:
        slicer.util.selectModule("Plots")
        # Asignar chart al PlotView
        plotWidget = slicer.app.layoutManager().plotWidget(0)
        if plotWidget:
            plotView = plotWidget.plotView()
            if plotView:
                plotView.SetChartNodeID(chart_node.GetID())
        slicer.app.processEvents()

    # Exportar imagen PNG
    try:
        dvh_png = os.path.join(OUTPUT_DIR_DEFAULT, "DVH_plot.png")
        _export_dvh_png(dvh_curves, dvh_png)
        logger.info(f"  DVH PNG: {dvh_png}")
    except Exception as e:
        logger.warning(f"  No se pudo exportar DVH PNG: {e}")

    return chart_node


def _export_dvh_png(dvh_curves, filepath):
    """Exporta DVH como PNG usando matplotlib (si disponible).

    dvh_curves: list of (name, d_vals_array, a_vals_array)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        colors = {"Higado": (0.2, 0.4, 1.0), "Tumor": (1.0, 0.2, 0.2), "Pretumor": (0.2, 1.0, 0.2)}

        fig, ax = plt.subplots(figsize=(10, 6))
        for name, d_vals, a_vals in dvh_curves:
            c = colors.get(name, (0.5, 0.5, 0.5))
            ax.plot(d_vals, a_vals, color=c, label=name, linewidth=2)

        ax.set_xlabel("Dose (Gy)", fontweight="bold")
        ax.set_ylabel("Volume (%)", fontweight="bold")
        ax.set_title("Cumulative Dose Volume Histogram", fontweight="bold")
        ax.set_yscale("log")
        ax.set_ylim(0.1, 200)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(filepath, dpi=150)
        plt.close(fig)
        logger.info(f"  DVH PNG exportado: {filepath}")
    except ImportError:
        logger.warning("  matplotlib no disponible para exportar PNG")


# ======================================================================
# 6. Main
# ======================================================================

def setup_slicer_paths():
    """Configura sys.path para importar SlicerDosimLib. Retorna path o None."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log(f"  script_dir: {script_dir}")

    # Posibles rutas a SlicerDosimLib
    possible_paths = [
        # Desde PipelineOrchestrator/ -> ../../Modules/Scripted/SlicerDosim/SlicerDosimLib
        os.path.join(script_dir, "..", "..", "Modules",
                     "Scripted", "SlicerDosim", "SlicerDosimLib"),
        # Resolucion absoluta
        r"C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim"
        r"\Modules\Scripted\SlicerDosim\SlicerDosimLib",
    ]

    for p in possible_paths:
        abs_p = os.path.abspath(p)
        log(f"  Checking path: {abs_p} (exists={os.path.exists(abs_p)})")
        if os.path.exists(abs_p) and abs_p not in sys.path:
            sys.path.insert(0, abs_p)
            log(f"  Path agregado: {abs_p}")
            return abs_p

    log("ERROR: No se encontro SlicerDosimLib en sys.path")
    return None


def get_labelmap_array(labelmap_node):
    """Extrae array 3D del labelmap, transpone a (nx, ny, nz)."""
    import slicer

    arr = slicer.util.arrayFromVolume(labelmap_node)  # (nz, ny, nx)
    arr = arr.transpose(2, 1, 0).astype(np.int32)  # (nx, ny, nz)
    return arr


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de dosimetria desde escena existente"
    )
    parser.add_argument("--scene", default=None,
                        help=f"Ruta a escena .mrb (default: {SCENE_DEFAULT})")
    parser.add_argument("--mctal", default=None,
                        help=f"Ruta a archivo MCTAL (default: {MCTAL_DEFAULT})")
    parser.add_argument("--output-dir", default=OUTPUT_DIR_DEFAULT,
                        help="Directorio de salida para reportes")
    parser.add_argument("--activity", type=float, default=None,
                        help="Actividad en GBq (default: computar del PET)")
    parser.add_argument("--labelmap", default=None,
                        help=f"Ruta a labelmap NIfTI (default: {LABELMAP_DEFAULT})")
    parser.add_argument("--no-slicer", action="store_true",
                        help="No cargar en Slicer (solo parsear MCTAL)")
    parser.add_argument("--show", action="store_true",
                        help="Mantener Slicer abierto con resultados visibles")

    args, _ = parser.parse_known_args()

    scene_path = args.scene or SCENE_DEFAULT
    mctal_path = args.mctal or MCTAL_DEFAULT
    output_dir = args.output_dir

    os.makedirs(output_dir, exist_ok=True)

    t_start = time.time()
    log("SCRIPT MAIN STARTED")

    # ----------------------------------------------------------------
    # Setup
    # ----------------------------------------------------------------
    log("=" * 60)
    log(" 3Dosim Dosimetry Pipeline v3.14")
    log("=" * 60)

    found = setup_slicer_paths()
    log(f"  SlicerDosimLib path found: {found}")

    # ----------------------------------------------------------------
    # Cargar escena en Slicer
    # ----------------------------------------------------------------
    if not args.no_slicer:
        import slicer

        logger.info("\n--- Paso 1: Cargar escena ---")
        if not load_scene(scene_path):
            logger.error("Abortando: no se pudo cargar la escena")
            return 1

        logger.info("\n--- Paso 2: Buscar nodos ---")
        nodes = find_nodes()

        labelmap_nifti = args.labelmap or LABELMAP_DEFAULT
        if nodes["labelmap"] is None and os.path.exists(labelmap_nifti):
            logger.info(f"  Cargando labelmap desde NIfTI: {labelmap_nifti}")
            labelmap_node = slicer.util.loadVolume(labelmap_nifti)
            if labelmap_node:
                nodes["labelmap"] = labelmap_node
                logger.info(f"  Labelmap cargado: {labelmap_node.GetName()}")
            else:
                logger.error("  No se pudo cargar labelmap NIfTI")

        if nodes["labelmap"] is None:
            logger.error("No se encontro nodo labelmap en la escena ni en NIfTI")
            return 1

        ct_node = nodes["ct"]
        pet_node = nodes["pet"]
        labelmap_node = nodes["labelmap"]

        # Extraer labelmap
        labelmap = get_labelmap_array(labelmap_node)
        dims = labelmap.shape  # (nx, ny, nz)
        spacing = labelmap_node.GetSpacing()

        logger.info(f"  Labelmap shape: {dims}")
        logger.info(f"  Spacing: {spacing}")
        logger.info(f"  Indices unicos: {np.unique(labelmap)}")

        # Actividad
        if args.activity is not None:
            activity_gbq = args.activity
            activity_bq = activity_gbq * 1e9
        elif pet_node is not None:
            logger.info("\n--- Paso 3: Computar actividad desde PET ---")
            activity_bq = compute_activity_from_pet(pet_node)
            activity_gbq = activity_bq / 1e9
        else:
            logger.error("No hay PET y no se especifico --activity")
            return 1

        logger.info(f"  Actividad: {activity_bq:.2e} Bq = {activity_gbq:.4f} GBq")

    else:
        # Modo standalone (sin Slicer)
        logger.info("Modo standalone: solo parseo MCTAL")
        dims = (512, 512, 171)  # default
        labelmap = None
        activity_bq = 3e9  # default 3 GBq
        activity_gbq = 3.0

    # ----------------------------------------------------------------
    # Parsear MCTAL
    # ----------------------------------------------------------------
    logger.info("\n--- Paso 4: Parsear MCTAL ---")
    mctal_result = parse_mctal(mctal_path, dims)
    dose_mev_cm3 = mctal_result["dose_3d"]
    error_3d = mctal_result["uncertainty"]

    # ----------------------------------------------------------------
    # Convertir a Gy
    # ----------------------------------------------------------------
    logger.info("\n--- Paso 5: Convertir a Gy ---")

    # Tiempo de integracion (mean lifetime)
    t_meanlife_s = Y90_HALF_LIFE_H * 3600 / np.log(2)  # ~332,753 s

    if labelmap is not None:
        dose_gy = convert_to_gy(dose_mev_cm3, labelmap, activity_bq, t_meanlife_s)
    else:
        # Sin labelmap: usar densidad uniforme
        dose_gy = dose_mev_cm3 * MEV2J * t_meanlife_s * activity_bq * 1000

    # Aplicar filtro de error (MATLAB cargo_mctal.m:375-379)
    error_eliminar = 1.5
    bad_voxels = error_3d >= error_eliminar
    dose_gy[bad_voxels] = 0
    n_bad = np.sum(bad_voxels)
    logger.info(f"  Voxels eliminados por error>={error_eliminar}: {n_bad} ({n_bad/dose_gy.size*100:.2f}%)")

    # Eliminar dosis negativas (poca estadistica)
    n_neg = np.sum(dose_gy < 0)
    dose_gy[dose_gy < 0] = 0
    logger.info(f"  Voxels con dosis negativa: {n_neg}")

    logger.info(f"  Dosis en Gy: media={dose_gy[dose_gy>0].mean() if np.any(dose_gy>0) else 0:.2f}, "
                f"max={dose_gy.max():.2f}, "
                f"voxels no-cero={np.sum(dose_gy>0)}/{dose_gy.size}")

    # ----------------------------------------------------------------
    # Computar dosimetria por estructura
    # ----------------------------------------------------------------
    logger.info("\n--- Paso 6: Dosimetria por estructura ---")

    structures = {
        "higado": {"idx": LIVER_INDEX, "alpha_beta": ALPHA_BETA_LIVER, "is_tumor": False},
        "tumor": {"idx": TUMOR_INDEX, "alpha_beta": ALPHA_BETA_TUMOR, "is_tumor": True},
        "pretumor": {"idx": PRETUMOR_INDEX, "alpha_beta": ALPHA_BETA_TUMOR, "is_tumor": False},
    }

    results = {
        "metadata": {
            "scene": scene_path,
            "mctal": mctal_path,
            "activity_bq": activity_bq,
            "activity_gbq": activity_gbq,
            "dimensions": list(dims),
            "nps": mctal_result["nps"],
            "title": mctal_result["title"],
        },
        "structures": {},
        "mird": {},
    }

    for name, info in structures.items():
        idx = info["idx"]
        mask = labelmap == idx if labelmap is not None else None
        n_vox = np.sum(mask) if mask is not None else 0

        if n_vox == 0:
            logger.info(f"  {name} ({idx}): sin voxeles, saltando")
            continue

        # DVH
        dvh = compute_dvh(dose_gy, labelmap, idx)
        logger.info(f"  {name} ({idx}): "
                    f"{dvh['n_voxels']} voxels, "
                    f"Dmedia={dvh['mean_dose_gy']:.2f} Gy, "
                    f"D98={dvh['d98_gy']:.2f} Gy, "
                    f"D70={dvh['d70_gy']:.2f} Gy, "
                    f"D50={dvh['d50_gy']:.2f} Gy")

        # Radiobiologia
        bio = compute_biophysical(dvh, info["alpha_beta"], info["is_tumor"])
        logger.info(f"    BED={bio['bed_gy']:.2f} Gy, "
                    f"EUD={bio['eud_gy']:.2f} Gy, "
                    f"EQD2={bio['eqd2_gy']:.2f} Gy")

        results["structures"][name] = {
            "index": idx,
            "n_voxels": dvh["n_voxels"],
            "mean_dose_gy": dvh["mean_dose_gy"],
            "min_dose_gy": dvh["min_dose_gy"],
            "max_dose_gy": dvh["max_dose_gy"],
            "std_dose_gy": dvh["std_dose_gy"],
            "d98_gy": dvh["d98_gy"],
            "d70_gy": dvh["d70_gy"],
            "d50_gy": dvh["d50_gy"],
            "bed_gy": bio["bed_gy"],
            "eud_gy": bio["eud_gy"],
            "eqd2_gy": bio["eqd2_gy"],
        }

    # ----------------------------------------------------------------
    # MIRD partition model
    # ----------------------------------------------------------------
    logger.info("\n--- Paso 7: MIRD partition model ---")
    mird = compute_mird(dose_gy, labelmap, activity_gbq)
    results["mird"] = mird
    logger.info(f"  Hígado: {mird['liver']['mean_dose_gy']:.2f} Gy")
    logger.info(f"  Tumor:  {mird['tumor']['mean_dose_gy']:.2f} Gy")
    logger.info(f"  Pretumor: {mird['pretumor']['mean_dose_gy']:.2f} Gy")

    # ----------------------------------------------------------------
    # Exportar reporte
    # ----------------------------------------------------------------
    logger.info("\n--- Paso 8: Exportar reporte ---")

    # Reporte JSON
    report_path = os.path.join(output_dir, "dosimetria_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"  Reporte JSON: {report_path}")

    # Reporte texto
    report_txt_path = os.path.join(output_dir, "dosimetria_report.txt")
    with open(report_txt_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write(" REPORTE DE DOSIMETRIA 3Dosim\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Escena:  {scene_path}\n")
        f.write(f"MCTAL:   {mctal_path}\n")
        f.write(f"Actividad: {activity_gbq:.4f} GBq ({activity_bq:.2e} Bq)\n")
        f.write(f"NPS:     {mctal_result['nps']}\n")
        f.write(f"Dimensiones: {dims}\n\n")

        f.write("-" * 50 + "\n")
        f.write(" RESULTADOS POR ESTRUCTURA\n")
        f.write("-" * 50 + "\n\n")
        for name, s in results["structures"].items():
            f.write(f"  {name.upper()} (indice={s['index']}):\n")
            f.write(f"    Voxeles:     {s['n_voxels']}\n")
            f.write(f"    Dosis media: {s['mean_dose_gy']:.2f} Gy\n")
            f.write(f"    Dosis min:   {s['min_dose_gy']:.2f} Gy\n")
            f.write(f"    Dosis max:   {s['max_dose_gy']:.2f} Gy\n")
            f.write(f"    D98:         {s['d98_gy']:.2f} Gy\n")
            f.write(f"    D70:         {s['d70_gy']:.2f} Gy\n")
            f.write(f"    D50:         {s['d50_gy']:.2f} Gy\n")
            f.write(f"    BED:         {s['bed_gy']:.2f} Gy\n")
            f.write(f"    EUD:         {s['eud_gy']:.2f} Gy\n")
            f.write(f"    EQD2:        {s['eqd2_gy']:.2f} Gy\n\n")

        f.write("-" * 50 + "\n")
        f.write(" MIRD PARTITION MODEL\n")
        f.write("-" * 50 + "\n\n")
        f.write(f"  Actividad: {activity_gbq:.4f} GBq\n")
        f.write(f"  Higado:    {results['mird']['liver']['mean_dose_gy']:.2f} Gy\n")
        f.write(f"  Tumor:     {results['mird']['tumor']['mean_dose_gy']:.2f} Gy\n")
        f.write(f"  Pretumor:  {results['mird']['pretumor']['mean_dose_gy']:.2f} Gy\n")

        t_elapsed = time.time() - t_start
        f.write(f"\n  Tiempo total: {t_elapsed:.1f} s\n")

    logger.info(f"  Reporte TXT: {report_txt_path}")

    # ----------------------------------------------------------------
    # Crear nodo de dosis en Slicer
    # ----------------------------------------------------------------
    if not args.no_slicer:
        logger.info("\n--- Paso 9: Crear nodo de dosis 3D en Slicer ---")
        try:
            from dosimetry import DoseCalculator

            calc = DoseCalculator()
            ref_node = labelmap_node or ct_node
            dose_node = calc.create_dose_volume(dose_gy, ref_node)
            if dose_node:
                logger.info(f"  Nodo creado: {dose_node.GetName()}")
                # Mostrar dosis como overlay en slices
                slice_nodes = slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode")
                for sn in slice_nodes:
                    if ct_node:
                        sn.SetBackgroundVolumeID(ct_node.GetID())
                    sn.SetForegroundVolumeID(dose_node.GetID())
                    sn.SetForegroundOpacity(0.5)
                # Activar layout medico con 3D
                try:
                    slicer.util.setSliceViewerLayers(foreground=dose_node, foregroundOpacity=0.5)
                    logger.info("  Overlay de dosis activado en slices")
                except Exception as e:
                    logger.warning(f"  setSliceViewerLayers: {e}")
                # Guardar escena con dosis
                scene_out = os.path.join(output_dir, "3Dosim_dosis_scene.mrb")
                try:
                    slicer.util.saveScene(scene_out)
                    logger.info(f"  Escena guardada: {scene_out}")
                except Exception as e:
                    logger.warning(f"  No se pudo guardar escena: {e}")
            else:
                logger.warning("  create_dose_volume devolvio None")
        except Exception as e:
            logger.warning(f"  Error creando nodo de dosis: {e}")
            import traceback
            logger.warning(traceback.format_exc())

    # ----------------------------------------------------------------
    # Tiempo total
    # ----------------------------------------------------------------
    t_elapsed = time.time() - t_start
    logger.info(f"\n  Tiempo total: {t_elapsed:.1f} s")
    logger.info("  Pipeline completado exitosamente!")
    logger.info(f"  Reporte: {report_txt_path}")

    # ----------------------------------------------------------------
    # Crear graficos DVH en Slicer (algoritmo MATLAB f_HDV.m)
    # ----------------------------------------------------------------
    if not args.no_slicer:
        logger.info("\n--- Paso 10: Graficar DVH en Slicer ---")
        try:
            _create_dvh_plots_slicer(dose_gy, labelmap, spacing, args.show)
        except Exception as e:
            logger.warning(f"  Error creando DVH plots: {e}")
            import traceback
            logger.warning(traceback.format_exc())

    # Mantener Slicer abierto si --show
    if args.show:
        logger.info("  --show: Slicer queda abierto. Cerrar ventana para salir.")
        sys.stderr.flush()
        slicer.util.selectModule("Plots")
        slicer.app.processEvents()
        # Abrir el nodo de dosis en el slice viewer
        if dose_node:
            slicer.util.setSliceViewerLayers(foreground=dose_node, foregroundOpacity=0.4)
        # Layout: arriba plots, abajo slices
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        # NO usar slicer.app.exec() — el event loop ya esta corriendo
        # y exec() falla, permitiendo que el script termine y Slicer se cierre.
        # En vez: loop con processEvents() mantiene el script vivo.
        try:
            while True:
                slicer.app.processEvents()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
