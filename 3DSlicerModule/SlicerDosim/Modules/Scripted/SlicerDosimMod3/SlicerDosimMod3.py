"""
SlicerDosimMod3 - Analisis dosimetrico (Modulo 3).

Procesa output MCNP, calcula dosis 3D, DVH, TCP, NTCP, MIRD.
Comparte SlicerDosimLib con Modulo 1 y Modulo 2.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import qt
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleTest,
)

# Resuelve el Scripted/ real (funciona desde junctions en qt-scripted-modules
# gracias a realpath que sigue el junction hasta el destino)
_scripted_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)
if _scripted_dir not in sys.path:
    sys.path.insert(0, _scripted_dir)

from SlicerDosim.SlicerDosimLib import (
    DoseCalculator,
    DVHAnalyzer,
    MCTALParser,
    SlicerDosimUtils,
)


class SlicerDosimMod3(ScriptedLoadableModule):
    """Registra el Modulo 3 (Analisis) en 3D Slicer."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "SlicerDosimMod3"
        self.description = (
            "Modulo 3: Analisis dosimetrico. "
            "Calculo de dosis 3D, MIRD, DVH, TCP, NTCP, "
            "micro-dosimetria y exportacion de reportes."
        )
        self.categories = ["3Dosim"]
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


class SlicerDosimMod3Logic(ScriptedLoadableModuleLogic):
    """Logica del Modulo 3: analisis dosimetrico."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.dose_calc = DoseCalculator()
        self.dvh_analyzer = DVHAnalyzer()
        self.mctal_parser = MCTALParser()
        self.mctal_path = None
        self.dose_node = None

    def load_mctal(self, path: str) -> dict:
        self.mctal_path = path
        return self.mctal_parser.parse(path)

    def compute_dose_3d(self, mctal_data: dict, activity_gbq: float) -> Optional[object]:
        node = self.dose_calc.compute_dose_3d(mctal_data, None, activity_gbq)
        if node:
            self.dose_node = node
        return node

    def compute_mird(self, liver_vol: float, tumor_vol: float) -> dict:
        return self.dose_calc.compute_mird(liver_vol, tumor_vol)

    def compute_dvh(self, structure_name: str = "liver") -> dict:
        if not self.dose_node:
            return {}
        seg_node = self._find_segmentation()
        if not seg_node:
            return {}
        return self.dvh_analyzer.compute_dvh(self.dose_node, seg_node, structure_name)

    def compute_tcp(self) -> dict:
        return self.dvh_analyzer.compute_tcp(self.dose_node, self._find_segmentation())

    def compute_ntcp(self) -> dict:
        return self.dvh_analyzer.compute_ntcp(self.dose_node, self._find_segmentation())

    def _find_segmentation(self):
        collection = slicer.mrmlScene.GetNodesByClass("vtkMRMLSegmentationNode")
        collection.UnRegister(None)
        for i in range(collection.GetNumberOfItems()):
            node = collection.GetItemAsObject(i)
            name = node.GetName()
            if "Phantom" in name or "3Dosim" in name:
                return node
        return None


class SlicerDosimMod3Widget(ScriptedLoadableModuleWidget):
    """Widget del Modulo 3."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logic = SlicerDosimMod3Logic()
        self.logger = logging.getLogger(__name__)

    def setup(self):
        super().setup()
        ui_path = os.path.join(
            os.path.dirname(__file__), "Resources", "UI", "SlicerDosimMod3.ui"
        )
        if os.path.exists(ui_path):
            self.ui = slicer.util.loadUI(ui_path)
            self.layout.addWidget(self.ui)
        else:
            self.logger.warning(f"UI no encontrado: {ui_path}")
            self._build_fallback_ui()

        self._connect_signals()

    def _build_fallback_ui(self):
        from slicer.util import VTKWidget
        vtk_widget = VTKWidget()
        self.layout.addWidget(vtk_widget)

    def _connect_signals(self):
        try:
            self.ui.btnCargarMCTAL.connect("clicked()", self._on_cargar_mctal)
            self.ui.btnCalcularDosis.connect("clicked()", self._on_calcular_dosis)
            self.ui.btnCalcularMIRD.connect("clicked()", self._on_calcular_mird)
            self.ui.btnCalcularDVH.connect("clicked()", self._on_calcular_dvh)
            self.ui.btnCalcularTCP.connect("clicked()", self._on_calcular_tcp)
            self.ui.btnCalcularNTCP.connect("clicked()", self._on_calcular_ntcp)
            self.ui.btnMicroDosimetria.connect("clicked()", self._on_micro_dosimetria)
            self.ui.btnVisualizarDosis.connect("clicked", self._on_visualizar)
            self.ui.btnExportarReporte.connect("clicked()", self._on_exportar)
        except AttributeError as e:
            self.logger.error(f"Error conectando senales: {e}")

    def _on_cargar_mctal(self):
        path = qt.QFileDialog.getOpenFileName(
            self.parent, "Seleccionar MCTAL", "", "MCTAL (*.mctal);;All (*)"
        )
        if path:
            data = self.logic.load_mctal(path)
            if data.get("dose_3d") is not None:
                slicer.util.showStatusMessage("MCTAL cargado", 3000)
                self._log(f"MCTAL: {path}")
            else:
                slicer.util.warningDisplay("No se extrajo dosis 3D del MCTAL")

    def _on_calcular_dosis(self):
        activity, ok = qt.QInputDialog.getDouble(
            self.parent, "Actividad", "Actividad (GBq):", 1.0, 0.01, 100.0, 2
        )
        if not ok or not self.logic.mctal_path:
            return
        data = self.logic.load_mctal(self.logic.mctal_path)
        if data.get("dose_3d") is None:
            slicer.util.errorDisplay("Sin datos de dosis en MCTAL")
            return
        node = self.logic.compute_dose_3d(data, activity)
        if node:
            slicer.util.showStatusMessage("Dosis 3D calculada", 3000)
            self._log(f"Dosis 3D: {activity} GBq")

    def _on_calcular_mird(self):
        liver_vol, ok1 = qt.QInputDialog.getDouble(
            self.parent, "Higado", "Volumen higado (ml):", 1500, 100, 5000, 0
        )
        if not ok1:
            return
        tumor_vol, ok2 = qt.QInputDialog.getDouble(
            self.parent, "Tumor", "Volumen tumor (ml):", 100, 1, 2000, 0
        )
        if not ok2:
            return
        mird = self.logic.compute_mird(liver_vol, tumor_vol)
        msg = (
            f"MIRD: Actividad = {mird['activity_gbq']:.2f} GBq, "
            f"D_higado = {mird['liver_dose_gy']:.1f} Gy"
        )
        slicer.util.showStatusMessage(msg, 5000)
        self._log(msg)

    def _on_calcular_dvh(self):
        dvh = self.logic.compute_dvh("liver")
        if dvh:
            self._log(
                f"DVH: D_mean = {dvh.get('d_mean_gy', 0):.1f} Gy, "
                f"D70 = {dvh.get('d70_gy', 0):.1f} Gy"
            )
        else:
            slicer.util.warningDisplay("Calcule la dosis primero")

    def _on_calcular_tcp(self):
        tcp = self.logic.compute_tcp()
        self._log(f"TCP = {tcp.get('tcp', 0) * 100:.1f}%")

    def _on_calcular_ntcp(self):
        ntcp = self.logic.compute_ntcp()
        self._log(f"NTCP = {ntcp.get('ntcp', 0) * 100:.1f}%")

    def _on_micro_dosimetria(self):
        self._log("Micro-dosimetria: pendiente de implementacion")

    def _on_visualizar(self):
        slicer.util.showStatusMessage("Visualizar dosis", 3000)

    def _on_exportar(self):
        path = qt.QFileDialog.getSaveFileName(
            self.parent, "Guardar reporte", "", "PDF (*.pdf);;Text (*.txt)"
        )
        if path and hasattr(self.ui, 'txtReporte'):
            SlicerDosimUtils.export_report_to_pdf(
                self.ui.txtReporte.toPlainText(), path
            )
            slicer.util.showStatusMessage(f"Reporte: {path}", 3000)

    def _log(self, msg: str):
        if hasattr(self.ui, 'txtReporte'):
            self.ui.txtReporte.append(msg)
        self.logger.info(msg)


class SlicerDosimMod3Test(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_Mod3_load()

    def test_Mod3_load(self):
        self.delayDisplay("Cargando Modulo 3...")
        logic = SlicerDosimMod3Logic()
        self.assertIsNotNone(logic)
        self.delayDisplay("Modulo 3 OK")
