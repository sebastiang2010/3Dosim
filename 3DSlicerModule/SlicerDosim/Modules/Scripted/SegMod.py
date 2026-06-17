"""
SegMod - Modulo 1: Segmentacion.
Archivo plano para descubrimiento en Slicer.
Importa implementacion real desde el subdirectorio SlicerDosim/.
"""
import sys, os

_this_dir = os.path.dirname(os.path.realpath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

import qt
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
)


class SegMod(ScriptedLoadableModule):
    """Modulo 1: Segmentacion."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Segmentacion"
        self.categories = ["3Dosim"]
        self.description = (
            "Modulo 1: Segmentacion. "
            "Carga DICOM, segmenta con TotalSegmentator, "
            "crea tumor sintetico y exporta labelmap."
        )
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


# Re-exportar las clases reales del subdirectorio
from SlicerDosim.SlicerDosim import SlicerDosimWidget as SegModWidget
from SlicerDosim.SlicerDosim import SlicerDosimLogic as SegModLogic
from SlicerDosim.SlicerDosim import SlicerDosimTest as SegModTest
