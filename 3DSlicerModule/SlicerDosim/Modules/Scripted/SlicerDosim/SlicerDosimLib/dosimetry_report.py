"""
dosimetry_report.py — Generacion de reportes PDF para dosimetria.

Modulo separado que genera reportes PDF profesionales con:
  - Portada con metadatos del estudio
  - Parametros radiobiologicos (Y-90)
  - Formulas LaTeX renderizadas via matplotlib
  - Tablas dosimetricas por estructura
  - MIRD partition model
  - DVH acumulativo (opcional)

Dependencias:
  - reportlab (principal)
  - matplotlib (para formulas LaTeX y DVH)
  - pypdf (para verificacion)

Uso:
  from SlicerDosimLib.dosimetry_report import DosimetryReportGenerator
  
  generator = DosimetryReportGenerator()
  pdf_path = generator.generate(results, output_dir, dvh_curves)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Constantes radiobiologicas (MATLAB cargo_mctal.m lineas 278-288)
ALPHA_BETA_LIVER = 2.5  # Gy
ALPHA_BETA_TUMOR = 10  # Gy
MU_REPAIR = 0.28  # h^-1 (T_repair = 2.5 h)
Y90_HALF_LIFE_H = 64.1  # h
LAMDA_DECAY = np.log(2) / Y90_HALF_LIFE_H  # h^-1
MEV2J = 1.6e-13

# Densidades (g/cm³)
DENSIDAD_LIVER = 1.06
DENSIDAD_TUMOR = 1.06
DENSIDAD_PRETUMOR = 1.06
DENSIDAD_BODY = 1.0
DENSIDAD_AIR = 0.001

# Indices de tejido
LIVER_INDEX = 90
TUMOR_INDEX = 100
PRETUMOR_INDEX = 200


class DosimetryReportGenerator:
    """
    Generador de reportes PDF para dosimetria 3D.
    
    Produces reportes profesionales con tablas, graficos y formulas LaTeX.
    """
    
    def __init__(self):
        self.logger = logger
    
    def generate(
        self,
        results: dict,
        output_dir: str,
        dvh_curves: Optional[list] = None,
    ) -> Optional[str]:
        """
        Genera reporte PDF con reportlab (5 paginas):
          P1: Portada con metadatos y resumen ejecutivo
          P2: Parametros radiobiologicos + formulas
          P3: Resultados dosimetricos por estructura + MIRD
          P4: DVH acumulativo (matplotlib embebido)
          P5: Metricas DVH por estructura

        Args:
            results: dict con metadata, structures, mird
            output_dir: directorio donde guardar el PDF
            dvh_curves: list of (name, d_vals_array, a_vals_array)

        Returns:
            ruta al PDF generado, o None si fallo
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm, cm
            from reportlab.lib.colors import HexColor, Color, black, white, grey
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                             Table, TableStyle, PageBreak, Image,
                                             KeepTogether, HRFlowable)
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            self.logger.warning("reportlab no disponible — usando matplotlib como fallback")
            return self._generate_fallback(results, output_dir, dvh_curves)

        pdf_path = os.path.join(output_dir, "dosimetria_report.pdf")
        meta = results.get("metadata", {})
        structures = results.get("structures", {})
        mird = results.get("mird", {})

        # -- Paleta de colores profesional --
        C_PRIMARY = HexColor("#1B2A4A")
        C_ACCENT = HexColor("#2E86AB")
        C_HEADER_BG = HexColor("#1B2A4A")
        C_HEADER_FG = white
        C_LIGHT_BG = HexColor("#F0F4F8")
        C_GRAY = HexColor("#6B7280")
        C_DARK = HexColor("#1F2937")
        C_HIGADO = HexColor("#2563EB")
        C_TUMOR = HexColor("#DC2626")
        C_PERITUMORAL = HexColor("#D97706")
        C_BORDER = HexColor("#D1D5DB")
        C_SUCCESS = HexColor("#059669")
        C_BG_LIGHT = HexColor("#FAFBFC")

        struct_colors_hex = {"higado": C_HIGADO, "tumor": C_TUMOR, "pretumor": C_PERITUMORAL}
        struct_labels = {"higado": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}

        # -- Estilos --
        styles = getSampleStyleSheet()
        s_title = ParagraphStyle("Title2", parent=styles["Title"],
                                 fontSize=26, textColor=C_PRIMARY, spaceAfter=4,
                                 fontName="Helvetica-Bold")
        s_subtitle = ParagraphStyle("Sub", parent=styles["Normal"],
                                    fontSize=11, textColor=C_GRAY, alignment=TA_CENTER)
        s_heading = ParagraphStyle("Head", parent=styles["Heading2"],
                                   fontSize=14, textColor=C_PRIMARY, spaceBefore=14,
                                   spaceAfter=6, fontName="Helvetica-Bold")
        s_heading3 = ParagraphStyle("Head3", parent=styles["Heading3"],
                                    fontSize=11, textColor=C_ACCENT, spaceBefore=10,
                                    spaceAfter=4, fontName="Helvetica-Bold")
        s_normal = ParagraphStyle("Norm", parent=styles["Normal"],
                                  fontSize=10, textColor=C_DARK, leading=14)
        s_small = ParagraphStyle("Small", parent=styles["Normal"],
                                 fontSize=9, textColor=C_GRAY, leading=12)
        s_bold = ParagraphStyle("Bold", parent=styles["Normal"],
                                fontSize=10, textColor=C_DARK, leading=14,
                                fontName="Helvetica-Bold")

        def add_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setStrokeColor(C_ACCENT)
            canvas_obj.setLineWidth(0.5)
            canvas_obj.line(20 * mm, 20 * mm, A4[0] - 20 * mm, 20 * mm)
            canvas_obj.setFont("Helvetica", 7)
            canvas_obj.setFillColor(C_GRAY)
            canvas_obj.drawString(20 * mm, 15 * mm, "3Dosim v3.14 — Dosimetria 3D para Medicina Nuclear")
            canvas_obj.drawRightString(A4[0] - 20 * mm, 15 * mm,
                                       f"Pagina {doc.page} de 5")
            canvas_obj.restoreState()

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=25 * mm,
        )
        story = []
        usable_width = A4[0] - 40 * mm
        formula_images_to_clean = []

        # ================================================================
        # PAGINA 1: PORTADA EJECUTIVA
        # ================================================================
        header_data = [["REPORTE DE DOSIMETRIA"]]
        header_table = Table(header_data, colWidths=[usable_width], rowHeights=[50])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, -1), white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 20),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("3Dosim v3.14 — Dosimetria 3D para Medicina Nuclear", s_subtitle))
        story.append(Spacer(1, 2 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT))
        story.append(Spacer(1, 6 * mm))

        # Metadata
        story.append(Paragraph("Informacion del Estudio", s_heading))
        meta_left = [
            ["Escena:", meta.get("scene", "N/A").split("/")[-1].split("\\")[-1]],
            ["MCTAL:", meta.get("mctal", "N/A").split("/")[-1].split("\\")[-1]],
            ["Actividad:", f"{meta.get('activity_gbq', 0):.4f} GBq"],
        ]
        meta_right = [
            ["NPS:", f"{meta.get('nps', 0):,}"],
            ["Dimensiones:", str(meta.get("dimensions", []))],
            ["Generado:", time.strftime("%Y-%m-%d %H:%M")],
        ]
        meta_table = Table(
            [meta_left[i] + meta_right[i] for i in range(3)],
            colWidths=[25 * mm, 55 * mm, 25 * mm, usable_width - 105 * mm]
        )
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), C_PRIMARY),
            ("TEXTCOLOR", (2, 0), (2, -1), C_PRIMARY),
            ("TEXTCOLOR", (1, 0), (1, -1), C_DARK),
            ("TEXTCOLOR", (3, 0), (3, -1), C_DARK),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6 * mm))

        # Resumen ejecutivo
        story.append(Paragraph("Resumen Ejecutivo", s_heading))
        story.append(Spacer(1, 2 * mm))

        all_struct_order = [("higado", "Hígado", LIVER_INDEX, C_HIGADO),
                            ("tumor", "Tumor", TUMOR_INDEX, C_TUMOR),
                            ("pretumor", "Peritumoral", PRETUMOR_INDEX, C_PERITUMORAL)]

        resumen_headers = ["", "Estructura", "Voxeles", "Vol (cm\u00b3)", "Dmedia (Gy)", "BED (Gy)"]
        resumen_data = [resumen_headers]
        for key, label, idx, color in all_struct_order:
            s = structures.get(key, {})
            n_vox = s.get("n_voxels", 0)
            vol = s.get("volume_cm3", 0)
            dmedia = s.get("mean_dose_gy", 0)
            bed = s.get("bed_gy", 0)
            status = "\u2713" if n_vox > 0 else "\u2014"
            resumen_data.append([
                status,
                label,
                f"{n_vox:,}" if n_vox > 0 else "0",
                f"{vol:.1f}" if vol > 0 else "\u2014",
                f"{dmedia:.2f}" if n_vox > 0 else "\u2014",
                f"{bed:.2f}" if n_vox > 0 else "\u2014",
            ])

        resumen_col_w = [10 * mm, 30 * mm, 22 * mm, 22 * mm, 24 * mm, usable_width - 108 * mm]
        resumen_table = Table(resumen_data, colWidths=resumen_col_w)
        resumen_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
            ("TEXTCOLOR", (1, 1), (1, 1), C_HIGADO),
            ("TEXTCOLOR", (1, 2), (1, 2), C_TUMOR),
            ("TEXTCOLOR", (1, 3), (1, 3), C_PERITUMORAL),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ]
        resumen_table.setStyle(TableStyle(resumen_style))
        story.append(resumen_table)

        story.append(Spacer(1, 4 * mm))
        n_structs_ok = sum(1 for key, _, _, _ in all_struct_order if key in structures and structures[key].get("n_voxels", 0) > 0)
        story.append(Paragraph(
            f"<font color=\"#{C_SUCCESS.hexval()[2:]}\">&#10003;</font> "
            f"<b>{n_structs_ok}/3 estructuras</b> con datos dosimetricos",
            s_small
        ))
        story.append(PageBreak())

        # ================================================================
        # PAGINA 2: PARAMETROS RADIOBIOLOGICOS
        # ================================================================
        story.append(Paragraph("Parametros Radiobiologicos", s_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("Constantes del Modelo Y-90", s_heading3))
        params_data = [
            ["Parametro", "Valor", "Unidad"],
            ["Vida media (t1/2)", f"{Y90_HALF_LIFE_H:.1f}", "horas"],
            ["Constante de decaimiento (lambda)", f"{LAMDA_DECAY:.4f}", "h^-1"],
            ["Tasa de reparacion (mu)", f"{MU_REPAIR:.2f}", "h^-1"],
            ["Tiempo de reparacion (T1/mu)", f"{1/MU_REPAIR:.1f}", "horas"],
            ["Vida media (tau)", f"{Y90_HALF_LIFE_H * 3600 / np.log(2):.0f}", "segundos"],
            ["Conversion MeV a J", f"{MEV2J:.2e}", "J/MeV"],
            ["Constante K (MIRD)", "48.98", "J*s"],
        ]
        params_table = Table(params_data, colWidths=[55 * mm, 40 * mm, usable_width - 95 * mm])
        params_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (2, 0), (2, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
        ]))
        story.append(params_table)
        story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("Relaciones alpha/beta por Estructura", s_heading3))
        ab_data = [
            ["Estructura", "alpha/beta (Gy)", "Tipo biologico", "Indice"],
            ["Hígado", f"{ALPHA_BETA_LIVER:.1f}", "Tejido normal", f"{LIVER_INDEX}"],
            ["Tumor", f"{ALPHA_BETA_TUMOR:.1f}", "Tumor maligno", f"{TUMOR_INDEX}"],
            ["Peritumoral", f"{ALPHA_BETA_LIVER:.1f}", "Tejido normal", f"{PRETUMOR_INDEX}"],
        ]
        ab_table = Table(ab_data, colWidths=[30 * mm, 25 * mm, 40 * mm, usable_width - 95 * mm])
        ab_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
            ("TEXTCOLOR", (0, 1), (0, 1), C_HIGADO),
            ("TEXTCOLOR", (0, 2), (0, 2), C_TUMOR),
            ("TEXTCOLOR", (0, 3), (0, 3), C_PERITUMORAL),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ]
        ab_table.setStyle(TableStyle(ab_style))
        story.append(ab_table)
        story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("Densidades Asignadas", s_heading3))
        dens_data = [
            ["Material", "Densidad (g/cm3)", "Uso"],
            ["Hígado / Tumor / Peritumoral", f"{DENSIDAD_LIVER:.2f}", "Tejido hepatico"],
            ["Body (default)", f"{DENSIDAD_BODY:.1f}", "Contorno corporal"],
            ["Aire", f"{DENSIDAD_AIR:.3f}", "Exterior"],
        ]
        dens_table = Table(dens_data, colWidths=[50 * mm, 35 * mm, usable_width - 85 * mm])
        dens_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
        ]))
        story.append(dens_table)
        story.append(Spacer(1, 6 * mm))

        # Formulas con LaTeX via matplotlib
        story.append(Paragraph("Formulas de Conversion", s_heading3))
        story.append(Spacer(1, 2 * mm))

        def _render_latex_to_image(latex_str, filepath, dpi=150, fontsize=14):
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(usable_width / cm, 1.2))
            ax.text(0.02, 0.5, f"${latex_str}$", fontsize=fontsize,
                    va="center", ha="left", transform=ax.transAxes)
            ax.axis("off")
            fig.savefig(filepath, dpi=dpi, bbox_inches="tight",
                        pad_inches=0.05, facecolor="white", transparent=False)
            plt.close(fig)

        formula_defs = [
            (r"\mathrm{BED} = D + \frac{\lambda}{(\alpha/\beta)(\lambda + \mu)} \cdot D^2",
             "Biologically Effective Dose"),
            (r"\mathrm{EUD} = \left( \sum_i v_i \cdot D_i^a \right)^{1/a}",
             "Equivalent Uniform Dose"),
            (r"\mathrm{EQD2} = \frac{\mathrm{BED}}{1 + \frac{2}{\alpha/\beta}}",
             "Equivalent Dose in 2 Gy fractions"),
            (r"D\,[\mathrm{Gy}] = D\,[\mathrm{MeV/g}] \times 1.6 \times 10^{-13} \times \tau \times \mathrm{Act} \times 1000",
             "Conversion MeV/cm\u00b3 a Gy"),
        ]

        formula_images = []
        for i, (latex, desc) in enumerate(formula_defs):
            img_path = os.path.join(output_dir, f"_formula_{i}.png")
            try:
                _render_latex_to_image(latex, img_path)
                formula_images.append((img_path, desc))
                formula_images_to_clean.append(img_path)
            except Exception as e:
                story.append(Paragraph(f"\u2022 <b>{desc}</b>: {latex}", s_small))

        if formula_images:
            img_w = (usable_width - 5 * mm) / 2
            img_h = img_w * 0.22
            for idx in range(0, len(formula_images), 2):
                row_items = []
                for j in range(2):
                    if idx + j < len(formula_images):
                        img_path, desc = formula_images[idx + j]
                        img_obj = Image(img_path, width=img_w, height=img_h)
                        row_items.append([img_obj, Paragraph(
                            f"<font color=\"#{C_GRAY.hexval()[2:]}\"><i>{desc}</i></font>",
                            ParagraphStyle("FormulaDesc", parent=s_small,
                                           fontSize=8, alignment=TA_CENTER)
                        )])
                    else:
                        row_items.append(["", ""])
                cell_left = row_items[0]
                cell_right = row_items[1] if len(row_items) > 1 else ["", ""]
                formula_table_data = [
                    [cell_left[0], cell_right[0]],
                    [cell_left[1], cell_right[1]],
                ]
                formula_table = Table(formula_table_data, colWidths=[img_w + 5 * mm, img_w + 5 * mm])
                formula_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, C_BORDER),
                ]))
                story.append(formula_table)
                story.append(Spacer(1, 2 * mm))

        story.append(PageBreak())

        # ================================================================
        # PAGINA 3: RESULTADOS DOSIMETRICOS + MIRD
        # ================================================================
        story.append(Paragraph("Resultados Dosimetricos por Estructura", s_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
        story.append(Spacer(1, 4 * mm))

        res_headers = ["Estructura", "Voxeles", "Vol (cm\u00b3)", "Dmedia (Gy)",
                       "D98 (Gy)", "D70 (Gy)", "D50 (Gy)", "BED (Gy)",
                       "EUD (Gy)", "EQD2 (Gy)"]
        res_data = [res_headers]
        for key, label, idx, color in all_struct_order:
            s = structures.get(key, {})
            res_data.append([
                label,
                f"{s.get('n_voxels', 0):,}" if s.get('n_voxels', 0) > 0 else "0",
                f"{s.get('volume_cm3', 0):.1f}" if s.get('volume_cm3', 0) > 0 else "\u2014",
                f"{s.get('mean_dose_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('d98_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('d70_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('d50_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('bed_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('eud_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                f"{s.get('eqd2_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
            ])
        res_col_w = usable_width / 10
        res_table = Table(res_data, colWidths=[res_col_w] * 10)
        res_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
        ]
        for i, (key, label, idx, color) in enumerate(all_struct_order, start=1):
            res_style.append(("TEXTCOLOR", (0, i), (0, i), color))
            res_style.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
        res_table.setStyle(TableStyle(res_style))
        story.append(res_table)
        story.append(Spacer(1, 10 * mm))

        # MIRD Partition Model
        story.append(Paragraph("MIRD Partition Model", s_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
        story.append(Spacer(1, 4 * mm))

        mird_key_map = {"higado": "liver", "tumor": "tumor", "pretumor": "pretumor"}
        mird_headers = ["Estructura", "Dmedia (Gy)", "Indice", "Tipo"]
        mird_data = [mird_headers]
        for key, label, idx, color in all_struct_order:
            mird_key = mird_key_map.get(key, key)
            dose_val = mird.get(mird_key, {}).get("mean_dose_gy", 0)
            tipo = "Tumor" if key == "tumor" else "Normal"
            mird_data.append([
                label,
                f"{dose_val:.2f}" if dose_val > 0 else "\u2014",
                f"{idx}",
                tipo,
            ])
        mird_table = Table(mird_data, colWidths=[35 * mm, 30 * mm, 20 * mm, usable_width - 85 * mm])
        mird_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
            ("TEXTCOLOR", (0, 1), (0, 1), C_HIGADO),
            ("TEXTCOLOR", (0, 2), (0, 2), C_TUMOR),
            ("TEXTCOLOR", (0, 3), (0, 3), C_PERITUMORAL),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ]
        mird_table.setStyle(TableStyle(mird_style))
        story.append(mird_table)

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(
            f"<font color=\"#{C_GRAY.hexval()[2:]}\">Actividad total: "
            f"{meta.get('activity_gbq', 0):.4f} GBq</font>",
            s_small
        ))
        story.append(PageBreak())

        # ================================================================
        # PAGINA 4: DVH
        # ================================================================
        if dvh_curves:
            story.append(Paragraph("Cumulative Dose Volume Histogram (DVH)", s_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
            story.append(Spacer(1, 4 * mm))

            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                dvh_colors = {"Hígado": (0.145, 0.388, 0.922), "Tumor": (0.863, 0.149, 0.149),
                              "Peritumoral": (0.851, 0.467, 0.024)}

                fig, ax = plt.subplots(figsize=(7.5, 4.5))
                for name, d_vals, a_vals in dvh_curves:
                    c = dvh_colors.get(name, (0.5, 0.5, 0.5))
                    ax.plot(d_vals, a_vals, color=c, label=name, linewidth=2.5)
                ax.set_xlabel("Dose (Gy)", fontsize=12, fontweight="bold")
                ax.set_ylabel("Volume (%)", fontsize=12, fontweight="bold")
                ax.set_title("Cumulative DVH", fontsize=14, fontweight="bold", pad=10)
                ax.set_yscale("log")
                ax.set_ylim(0.1, 200)
                ax.grid(True, which="both", alpha=0.3, linestyle="--")
                ax.legend(fontsize=11, loc="upper right", framealpha=0.9)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()

                dvh_img_path = os.path.join(output_dir, "_dvh_temp.png")
                fig.savefig(dvh_img_path, dpi=150, bbox_inches="tight", facecolor="white")
                plt.close(fig)

                img = Image(dvh_img_path, width=usable_width, height=usable_width * 0.6)
                story.append(img)
                story.append(Spacer(1, 6 * mm))

                try:
                    os.remove(dvh_img_path)
                except Exception:
                    pass
            except Exception as e:
                story.append(Paragraph(f"Error generando DVH: {e}", s_small))

            story.append(PageBreak())

            # ================================================================
            # PAGINA 5: METRICAS DVH
            # ================================================================
            story.append(Paragraph("Metricas DVH por Estructura", s_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
            story.append(Spacer(1, 4 * mm))

            dvh_headers = ["Estructura", "Vol (cm\u00b3)", "Dmedia (Gy)", "D98 (Gy)",
                           "D70 (Gy)", "D50 (Gy)", "Max (Gy)", "BED (Gy)", "EUD (Gy)"]
            dvh_data = [dvh_headers]
            for key, label, idx, color in all_struct_order:
                s = structures.get(key, {})
                dvh_data.append([
                    label,
                    f"{s.get('volume_cm3', 0):.1f}" if s.get('volume_cm3', 0) > 0 else "\u2014",
                    f"{s.get('mean_dose_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('d98_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('d70_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('d50_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('max_dose_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('bed_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                    f"{s.get('eud_gy', 0):.2f}" if s.get('n_voxels', 0) > 0 else "\u2014",
                ])
            dvh_col_w = usable_width / 9
            dvh_table = Table(dvh_data, colWidths=[dvh_col_w] * 9)
            dvh_style = [
                ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG_LIGHT]),
            ]
            for i, (key, label, idx, color) in enumerate(all_struct_order, start=1):
                dvh_style.append(("TEXTCOLOR", (0, i), (0, i), color))
                dvh_style.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
            dvh_table.setStyle(TableStyle(dvh_style))
            story.append(dvh_table)

        logger.info(f"Reporte PDF: {pdf_path}")
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)

        # Limpiar imagenes temporales
        for img_path in formula_images_to_clean:
            try:
                os.remove(img_path)
            except Exception:
                pass

        return pdf_path

    def _generate_fallback(
        self, results: dict, output_dir: str, dvh_curves: Optional[list] = None
    ) -> Optional[str]:
        """Fallback: genera PDF con matplotlib si reportlab no esta disponible."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            self.logger.warning("matplotlib no disponible para PDF")
            return None

        pdf_path = os.path.join(output_dir, "dosimetria_report.pdf")
        meta = results.get("metadata", {})
        structures = results.get("structures", {})

        struct_labels = {"higado": "Hígado", "tumor": "Tumor", "pretumor": "Peritumoral"}

        with PdfPages(pdf_path) as pdf:
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")
            ax.text(0.5, 0.9, "REPORTE DE DOSIMETRIA", fontsize=24,
                    fontweight="bold", ha="center", transform=ax.transAxes)
            ax.text(0.5, 0.85, "3Dosim v3.14", fontsize=12, ha="center",
                    color="#666", transform=ax.transAxes)
            y0 = 0.7
            for label, value in [
                ("Actividad", f"{meta.get('activity_gbq', 0):.4f} GBq"),
                ("NPS", f"{meta.get('nps', 0):,}"),
            ]:
                ax.text(0.15, y0, f"{label}: {value}", fontsize=11, transform=ax.transAxes)
                y0 -= 0.04
            y0 -= 0.03
            ax.text(0.15, y0, "ESTRUCTURAS:", fontsize=12, fontweight="bold",
                    transform=ax.transAxes)
            y0 -= 0.04
            for name, s in structures.items():
                label = struct_labels.get(name, name)
                ax.text(0.15, y0,
                        f"  {label}: Dmedia={s.get('mean_dose_gy',0):.2f} Gy, "
                        f"BED={s.get('bed_gy',0):.2f} Gy",
                        fontsize=10, transform=ax.transAxes)
                y0 -= 0.03
            pdf.savefig(fig)
            plt.close(fig)

        self.logger.info(f"Reporte PDF (fallback matplotlib): {pdf_path}")
        return pdf_path
