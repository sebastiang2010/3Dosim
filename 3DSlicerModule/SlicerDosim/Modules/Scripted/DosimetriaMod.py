"""
DosimetriaMod - Modulo 2: Dosimetria (generacion MCNP).
Archivo plano para descubrimiento en Slicer.
Importa implementacion real desde el subdirectorio SlicerDosimMod2/.
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


class DosimetriaMod(ScriptedLoadableModule):
    """Modulo 2: Dosimetria (generacion MCNP)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Dosimetria"
        self.categories = ["3Dosim"]
        self.description = (
            "Modulo 2: Dosimetria. "
            "Genera entrada MCNP con geometria voxelizada, "
            "materiales del phantom y fuente desde PET."
        )
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


# Re-exportar las clases reales del subdirectorio
from SlicerDosimMod2.SlicerDosimMod2 import SlicerDosimMod2Widget as DosimetriaModWidget
from SlicerDosimMod2.SlicerDosimMod2 import SlicerDosimMod2Logic as DosimetriaModLogic
from SlicerDosimMod2.SlicerDosimMod2 import SlicerDosimMod2Test as DosimetriaModTest
