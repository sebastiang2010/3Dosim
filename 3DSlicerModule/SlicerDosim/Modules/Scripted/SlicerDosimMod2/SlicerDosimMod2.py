"""
SlicerDosimMod2 - Generacion de entrada MCNP (Modulo 2).

Independiente del Modulo 1. Comparte SlicerDosimLib con los otros modulos.
Requiere el phantom labelmap generado por SlicerDosim (Modulo 1).
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

_scripted_dir = os.path.join(os.path.dirname(__file__), "..")
if _scripted_dir not in sys.path:
    sys.path.insert(0, _scripted_dir)

from SlicerDosim.SlicerDosimLib import (
    MCNPInputGenerator,
    MCTALParser,
    TissueConfig,
)


class SlicerDosimMod2(ScriptedLoadableModule):
    """Registra el Modulo 2 (MCNP) en 3D Slicer."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "SlicerDosimMod2"
        self.description = (
            "Modulo 2: Generacion de entrada MCNP. "
            "Construye geometria voxelizada, asigna materiales del phantom, "
            "define fuente desde PET y configura tallies de dosis."
        )
        self.categories = ["3Dosim"]
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


class SlicerDosimMod2Logic(ScriptedLoadableModuleLogic):
    """Logica del Modulo 2: orquesta generacion MCNP."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = TissueConfig()
        self.mcnp_gen = MCNPInputGenerator()
        self.mctal_parser = MCTALParser()
        self.output_path = None

    def generate_mcnp(
        self,
        ct_node,
        pet_node,
        segmentation_node,
        output_dir: str,
        isotope: str = "Y-90",
        n_particles: int = int(1e7),
        refine_hu: bool = False,
    ) -> Optional[str]:
        """Genera archivo MCNP .i usando el orquestador."""
        self.logger.info(f"Generando MCNP para {isotope} ({n_particles} particulas)")
        input_path = self.mcnp_gen.generate(
            ct_volume_node=ct_node,
            pet_volume_node=pet_node,
            segmentation_node=segmentation_node,
            output_dir=output_dir,
            isotope=isotope,
            n_particles=n_particles,
            refine_hu=refine_hu,
        )
        self.output_path = input_path
        return input_path

    def load_mctal(self, mctal_path: str) -> dict:
        """Carga y parsea archivo MCTAL."""
        return self.mctal_parser.parse(mctal_path)


class SlicerDosimMod2Widget(ScriptedLoadableModuleWidget):
    """Widget del Modulo 2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logic = SlicerDosimMod2Logic()
        self.logger = logging.getLogger(__name__)

    def setup(self):
        super().setup()
        ui_path = os.path.join(
            os.path.dirname(__file__), "Resources", "UI", "SlicerDosimMod2.ui"
        )
        if os.path.exists(ui_path):
            self.ui = slicer.util.loadUI(ui_path)
            self.layout.addWidget(self.ui)
        else:
            self.logger.warning(f"UI no encontrado: {ui_path}")
            self._build_fallback_ui()

        self._connect_signals()
        self._update_ui_state()

    def _build_fallback_ui(self):
        from slicer.util import VTKWidget
        vtk_widget = VTKWidget()
        self.layout.addWidget(vtk_widget)

    def _connect_signals(self):
        try:
            self.ui.btnGenerarMCNP.connect("clicked()", self._on_generar)
            self.ui.btnEjecutarMCNP.connect("clicked()", self._on_ejecutar)
            self.ui.btnCargarMCTAL.connect("clicked()", self._on_cargar_mctal)
            self.ui.btnVisualizarDosis.connect("clicked", self._on_visualizar)
        except AttributeError as e:
            self.logger.error(f"Error conectando senales: {e}")

    def _on_generar(self):
        """Generar entrada MCNP."""
        output_dir = qt.QFileDialog.getExistingDirectory(
            self.parent, "Directorio para archivos MCNP"
        )
        if not output_dir:
            return

        isotope = self.ui.comboIsotopo.currentText
        n_parts = int(self.ui.spinNumParticulas.value)
        refine = self.ui.chkRefinarHU.isChecked() if hasattr(self.ui, 'chkRefinarHU') else False

        # Buscar nodos en la escena
        ct_node = self._find_node("CT")
        pet_node = self._find_node("PET")
        seg_node = self._find_segmentation()

        if ct_node is None:
            slicer.util.errorDisplay("No se encuentra volumen CT en la escena.")
            return
        if seg_node is None:
            slicer.util.errorDisplay(
                "No se encuentra segmentacion del phantom. "
                "Ejecute primero SlicerDosim (Modulo 1) > Pipeline completo."
            )
            return

        slicer.util.showStatusMessage("Generando entrada MCNP...", 10000)
        try:
            input_path = self.logic.generate_mcnp(
                ct_node, pet_node, seg_node, output_dir,
                isotope=isotope, n_particles=n_parts, refine_hu=refine,
            )
            if input_path:
                slicer.util.showStatusMessage(f"MCNP generado: {input_path}", 5000)
                if hasattr(self.ui, 'txtInfo'):
                    self.ui.txtInfo.append(f"Input MCNP: {input_path}")
        except Exception as e:
            slicer.util.errorDisplay(f"Error generando MCNP: {e}")

    def _on_ejecutar(self):
        """Ejecutar MCNP (placeholder)."""
        slicer.util.showStatusMessage(
            "Ejecute MCNP manualmente desde la terminal", 5000
        )

    def _on_cargar_mctal(self):
        """Cargar archivo MCTAL."""
        file_path = qt.QFileDialog.getOpenFileName(
            self.parent, "Seleccionar MCTAL", "", "MCTAL (*.mctal);;All (*)"
        )
        if file_path:
            data = self.logic.load_mctal(file_path)
            if data.get("dose_3d") is not None:
                slicer.util.showStatusMessage(
                    f"MCTAL cargado: {os.path.basename(file_path)}", 3000
                )
                if hasattr(self.ui, 'txtInfo'):
                    self.ui.txtInfo.append(f"MCTAL: {file_path}")
            else:
                slicer.util.warningDisplay(
                    "Archivo MCTAL cargado pero no se extrajo dosis 3D."
                )

    def _on_visualizar(self):
        """Visualizar dosis (placeholder)."""
        slicer.util.showStatusMessage("Visualizar dosis: cargue MCTAL primero", 3000)

    def _find_node(self, keyword: str):
        """Busca un volumen por keyword en el nombre."""
        collection = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
        collection.UnRegister(None)
        for i in range(collection.GetNumberOfItems()):
            node = collection.GetItemAsObject(i)
            name = node.GetName().upper()
            if keyword in name:
                return node
        return None

    def _find_segmentation(self):
        """Busca segmentation node del phantom."""
        collection = slicer.mrmlScene.GetNodesByClass("vtkMRMLSegmentationNode")
        collection.UnRegister(None)
        for i in range(collection.GetNumberOfItems()):
            node = collection.GetItemAsObject(i)
            name = node.GetName()
            if "Phantom" in name or "3Dosim" in name:
                return node
        return None

    def _update_ui_state(self):
        pass


class SlicerDosimMod2Test(ScriptedLoadableModuleTest):
    """Tests del Modulo 2."""

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_Mod2_load()

    def test_Mod2_load(self):
        self.delayDisplay("Cargando Modulo 2...")
        logic = SlicerDosimMod2Logic()
        self.assertIsNotNone(logic)
        self.delayDisplay("Modulo 2 OK")
