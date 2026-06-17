"""
AnalisisMod - Modulo 3: Analisis dosimetrico (post-procesamiento MCNP).
Archivo plano para descubrimiento en Slicer.
Importa implementacion real desde el subdirectorio SlicerDosimMod3/.
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


class AnalisisMod(ScriptedLoadableModule):
    """Modulo 3: Analisis dosimetrico."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Analisis"
        self.categories = ["3Dosim"]
        self.description = (
            "Modulo 3: Analisis. "
            "Procesa output MCNP, calcula dosis 3D, DVH, TCP, NTCP."
        )
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


# Re-exportar las clases reales del subdirectorio
from SlicerDosimMod3.SlicerDosimMod3 import SlicerDosimMod3Widget as AnalisisModWidget
from SlicerDosimMod3.SlicerDosimMod3 import SlicerDosimMod3Logic as AnalisisModLogic
from SlicerDosimMod3.SlicerDosimMod3 import SlicerDosimMod3Test as AnalisisModTest
