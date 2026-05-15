"""
Modulo de calculo dosimetrico para SlicerDosim.

Procesa el output MCNP (archivos MCTAL) y genera mapas de dosis 3D.
Incluye tanto metodo Monte Carlo como metodo analitico MIRD.

Delega el parseo MCTAL a mctal_parser.py.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .mctal_parser import MCTALParser


class DoseCalculator:
    """
    Calculador de dosis a partir de simulaciones MCNP.

    Lee archivos MCTAL via MCTALParser, extrae dosis por voxel,
    y genera volumenes de dosis 3D en el escenario de 3D Slicer.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser = MCTALParser()

    def load_mctal(self, mctal_path: str) -> dict:
        """
        Carga un archivo MCTAL de salida MCNP.

        Args:
            mctal_path: ruta al archivo MCTAL

        Returns:
            dict con datos de dosis estructurados:

            Claves principales:
              - 'dose_3d': array 3D de dosis (MeV/g/particula)
              - 'uncertainty': array 3D de incertidumbre
              - 'dimensions': (nx, ny, nz)
              - 'tally_data': dict con datos de cada tally
              - 'title': titulo del problema
              - 'nps': numero de historias
        """
        if not os.path.exists(mctal_path):
            raise FileNotFoundError(f"Archivo MCTAL no encontrado: {mctal_path}")

        self.logger.info(f"Cargando MCTAL: {mctal_path}")

        dose_data = self.parser.parse(mctal_path)
        return dose_data

    def compute_dose_3d(
        self, mctal_data: dict, volume_node, activity_gbq: float = 1.0
    ) -> Optional[object]:
        """
        Convierte dosis del MCTAL a mapa de dosis 3D en Gy.

        La conversion es:
            D_Gy = D_MCTAL * Actividad_GBq * k

        donde k = 49.98 J-s (constante de conversion).

        Args:
            mctal_data: datos parseados del MCTAL
            volume_node: volumen de referencia para metadatos
            activity_gbq: actividad administrada en GBq

        Returns:
            nodo de volumen escalar con la dosis 3D en Gy
        """
        try:
            import slicer
            import numpy as np

            # Obtener array de dosis
            dose_raw = mctal_data.get("dose_3d")
            if dose_raw is None:
                raise ValueError("No hay datos de dosis en MCTAL")

            # Convertir a Gy
            k = 49.98  # J-s, conversion MCNP -> Gy
            dose_gy = np.array(dose_raw) * activity_gbq * k

            # Crear volumen en Slicer
            dose_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode", "Dosis_3D_Gy"
            )

            import vtk
            vtk_array = vtk.vtkDoubleArray()
            vtk_array.SetNumberOfValues(dose_gy.size)
            for i, val in enumerate(dose_gy.flat):
                vtk_array.SetValue(i, float(val))

            # Configurar imagen VTK
            vtk_image = vtk.vtkImageData()
            dims = mctal_data.get("dimensions", dose_gy.shape)
            vtk_image.SetDimensions(dims)
            vtk_image.GetPointData().SetScalars(vtk_array)

            # Copiar espaciado y origen del volumen de referencia
            if volume_node:
                vtk_image.SetSpacing(volume_node.GetSpacing())
                vtk_image.SetOrigin(volume_node.GetOrigin())

            dose_node.SetAndObserveImageData(vtk_image)
            self.logger.info(f"Dosis 3D creada: {dose_gy.sum():.2f} Gy total")

            return dose_node

        except Exception as e:
            self.logger.error(f"Error calculando dosis 3D: {e}")
            return None

    def compute_mird(
        self,
        liver_volume_ml: float,
        tumor_volume_ml: float,
        shunt_fraction: float = 0.05,
        target_dose_gy: float = 150.0,
        t_n_ratio: float = 2.8,
    ) -> dict:
        """
        Calculo analitico MIRD para planificacion Y-90.

        Implementa el modelo del MIRD pam 103 (Libro Y-90).

        Args:
            liver_volume_ml: volumen de higado sano (ml)
            tumor_volume_ml: volumen tumoral (ml)
            shunt_fraction: fraccion de shunt pulmonar (SF)
            target_dose_gy: dosis target al tumor (Gy)
            t_n_ratio: relacion tumor/normal (T/N)

        Returns:
            dict con actividad requerida (GBq) y dosis a higado normal (Gy)
        """
        k = 49.98  # J-s (Gy * kg / GBq)

        # Fracciones de uptake
        fu_normal = (1 - shunt_fraction) * (
            liver_volume_ml / (t_n_ratio * tumor_volume_ml + liver_volume_ml)
        )
        fu_tumor = (1 - shunt_fraction) * (
            t_n_ratio * tumor_volume_ml / (t_n_ratio * tumor_volume_ml + liver_volume_ml)
        )

        # Masa (asumiendo densidad 1.0 g/ml)
        m_tumor = tumor_volume_ml / 1000  # kg
        m_normal = liver_volume_ml / 1000  # kg

        # Actividad necesaria
        actividad_gbq = target_dose_gy * m_tumor / (k * fu_tumor)
        d_normal_gy = actividad_gbq * k * fu_normal / m_normal

        return {
            "activity_gbq": actividad_gbq,
            "liver_dose_gy": d_normal_gy,
            "tumor_dose_gy": target_dose_gy,
            "fu_tumor": fu_tumor,
            "fu_normal": fu_normal,
        }

    def compute_dose_kernel(
        self, pet_volume_node, kernel_3d: dict
    ) -> Optional[object]:
        """
        Convoluciona el volumen PET con un kernel de dosis
        precalculado (aproximacion rapida sin MCNP).
        """
        # Placeholder: implementacion de convolution 3D
        return None
