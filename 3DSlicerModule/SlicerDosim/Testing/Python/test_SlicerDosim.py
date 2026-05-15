"""
Tests unitarios para SlicerDosim.

Ejecutar con:
  slicer --python-script test_SlicerDosim.py
  pytest test_SlicerDosim.py
"""

import sys
import os

# Agregar ruta del modulo
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "Modules",
        "Scripted",
        "SlicerDosim",
    ),
)

from SlicerDosimLib import (
    LiverSegmenter,
    DosimetryRegistration,
    MCNPInputGenerator,
    DoseCalculator,
    DVHAnalyzer,
    SlicerDosimUtils,
)


class TestSlicerDosimUtils:
    """Tests de utilidades."""

    def test_hu_to_density_water(self):
        density = SlicerDosimUtils.hu_to_density(0)
        assert abs(density - 1.0) < 0.01

    def test_hu_to_density_air(self):
        density = SlicerDosimUtils.hu_to_density(-1000)
        assert abs(density - 0.001) < 0.001

    def test_hu_to_density_bone(self):
        density = SlicerDosimUtils.hu_to_density(1000)
        assert abs(density - 1.9) < 0.1

    def test_activity_conversion(self):
        bq = SlicerDosimUtils.activity_gbq_to_bq(1.0)
        assert abs(bq - 1e9) < 1

    def test_dose_conversion(self):
        mgy = SlicerDosimUtils.dose_gy_to_mgy(1.0)
        assert abs(mgy - 1000) < 1


class TestDoseCalculator:
    """Tests de calculo dosimetrico."""

    def test_mird_calculation(self):
        calc = DoseCalculator()
        result = calc.compute_mird(
            liver_volume_ml=1500.0,
            tumor_volume_ml=100.0,
            shunt_fraction=0.05,
            target_dose_gy=150.0,
            t_n_ratio=2.8,
        )
        assert result["activity_gbq"] > 0
        assert result["liver_dose_gy"] > 0
        assert result["fu_tumor"] > result["fu_normal"]
        assert result["tumor_dose_gy"] == 150.0

    def test_mird_zero_tumor(self):
        calc = DoseCalculator()
        result = calc.compute_mird(
            liver_volume_ml=1500.0, tumor_volume_ml=0.0
        )
        assert result["activity_gbq"] == 0.0


class TestDVHAnalyzer:
    """Tests de analisis DVH."""

    def test_tcp_logistic(self):
        class MockNode:
            pass

        # Sin segmentacion, debe retornar error
        analyzer = DVHAnalyzer()
        result = analyzer.compute_tcp(None, None)
        assert result.get("tcp", -1) == 0.0


class TestMCNPInputGenerator:
    """Tests de generacion MCNP."""

    def test_isotope_data(self):
        from SlicerDosimLib.mcnp_generator import ISOTOPE_DATA
        assert "Y-90" in ISOTOPE_DATA
        assert "I-131" in ISOTOPE_DATA
        assert ISOTOPE_DATA["Y-90"]["zaid"] == 39090
