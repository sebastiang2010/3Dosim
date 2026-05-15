"""
Generador de archivos de entrada MCNP para SlicerDosim.

Orquesta los sub-modulos especializados para construir el archivo .i:
  - mcnp_materials: asignacion de materiales desde phantom
  - mcnp_geometry: geometria voxelizada con LIKE n BUT
  - mcnp_source: definicion de fuente desde PET
  - mcnp_tallies: FMESH4, F6, corte, NPS
"""

from __future__ import annotations

import logging
import os
import numpy as np
from typing import Optional

from .config import TissueConfig
from .mcnp_materials import MCNPMaterialMapper
from .mcnp_geometry import MCNPGeometryBuilder
from .mcnp_source import MCNPSourceBuilder
from .mcnp_tallies import MCNPTallyBuilder


logger = logging.getLogger(__name__)


ISOTOPE_DATA = {
    "Y-90": {
        "name": "Yttrium-90",
        "zaid": 39090,
        "half_life_days": 2.67,
        "energy_mev": 2.28,
        "particle": "electron",
        "mode": "e",
    },
    "I-131": {
        "name": "Iodine-131",
        "zaid": 53131,
        "half_life_days": 8.02,
        "energy_mev": 0.606,
        "particle": "electron",
        "mode": "e",
    },
    "Lu-177": {
        "name": "Lutetium-177",
        "zaid": 77177,
        "half_life_days": 6.65,
        "energy_mev": 0.498,
        "particle": "electron",
        "mode": "e",
    },
    "Tc-99m": {
        "name": "Technetium-99m",
        "zaid": 43099,
        "half_life_days": 0.25,
        "energy_mev": 0.140,
        "particle": "photon",
        "mode": "p",
    },
}


class MCNPInputGenerator:
    """
    Orquestador de generacion de entrada MCNP.

    Coordina los sub-modulos para producir un archivo .i completo:
      1. Extraer phantom labelmap desde el segmentation node
      2. Asignar materiales (MCNPMaterialMapper)
      3. Construir geometria (MCNPGeometryBuilder)
      4. Definir fuente (MCNPSourceBuilder)
      5. Configurar tallies (MCNPTallyBuilder)
      6. Escribir archivo .i
    """

    def __init__(self):
        self.config = TissueConfig()
        self.materials = MCNPMaterialMapper(self.config)
        self.geometry = MCNPGeometryBuilder(self.config)
        self.source_builder = MCNPSourceBuilder()
        self.tallies = MCNPTallyBuilder()

    def generate(
        self,
        ct_volume_node,
        pet_volume_node,
        segmentation_node,
        output_dir: str,
        isotope: str = "Y-90",
        n_particles: int = int(1e7),
        refine_hu: bool = False,
    ) -> str:
        """
        Genera el archivo de entrada MCNP.

        Args:
            ct_volume_node: vtkMRMLScalarVolumeNode del CT (para HU y geometria)
            pet_volume_node: vtkMRMLScalarVolumeNode del PET (para fuente)
            segmentation_node: vtkMRMLSegmentationNode del phantom 3Dosim
            output_dir: directorio de salida
            isotope: isotopo (Y-90, I-131, Lu-177, Tc-99m)
            n_particles: numero de historias MCNP
            refine_hu: si True, refina materiales por HU del CT

        Returns:
            ruta al archivo .i generado
        """
        iso_data = ISOTOPE_DATA.get(isotope)
        if iso_data is None:
            raise ValueError(f"Isotopo no soportado: {isotope}")

        logger.info(f"Generando entrada MCNP para {isotope}")
        logger.info(f"Particulas: {n_particles}")

        # 1. Obtener informacion del volumen CT
        dims, origin, spacing = self._get_volume_info(ct_volume_node)
        logger.info(f"  Dimensiones: {dims}, Espaciado: {spacing}")

        # 2. Extraer phantom labelmap desde el segmentation node
        phantom_arr = self._get_phantom_labelmap(segmentation_node, dims)
        if phantom_arr is None:
            raise RuntimeError(
                "No se pudo extraer labelmap del phantom. "
                "Ejecute la segmentacion primero."
            )
        logger.info(f"  Phantom indices: {sorted(np.unique(phantom_arr))}")

        # 3. Asignar materiales
        if refine_hu and ct_volume_node is not None:
            hu_arr = self._get_hu_array(ct_volume_node, dims)
            materials_arr = self.materials.assign_hu_refined(phantom_arr, hu_arr)
        else:
            materials_arr = self.materials.assign_from_labelmap(phantom_arr)

        mat_cards = self.materials.generate_material_cards()
        dens_cards = self.materials.generate_density_cards()
        logger.info(f"  Materiales generados: {len(mat_cards)} tarjetas")

        # 4. Construir geometria
        geom_cards = self.geometry.build(dims, origin, spacing, materials_arr)
        logger.info(f"  Geometria: {len(geom_cards)} tarjetas")

        # 5. Definir fuente
        liver_mask = (phantom_arr == 90) | (phantom_arr == 100)
        src_cards = self.source_builder.build(
            pet_volume_node, dims, iso_data, liver_mask
        )
        logger.info(f"  Fuente: {len(src_cards)} tarjetas")

        # 6. Tallies
        tal_cards = self.tallies.build(iso_data, dims, n_particles, origin)
        logger.info(f"  Tallies: {len(tal_cards)} tarjetas")

        # 7. Escribir archivo
        input_path = os.path.join(output_dir, "3Dosim_mcnp.i")
        self._write_input(
            input_path, iso_data, n_particles,
            dens_cards, mat_cards, geom_cards, src_cards, tal_cards,
        )

        logger.info(f"Archivo MCNP generado: {input_path}")
        return input_path

    def _get_volume_info(self, volume_node) -> tuple:
        """Obtiene dimensiones, origen y espaciado de un volumen."""
        try:
            import slicer
            image_data = volume_node.GetImageData()
            dims = image_data.GetDimensions()
            origin = volume_node.GetOrigin()
            spacing = volume_node.GetSpacing()
            return dims, origin, spacing
        except Exception as e:
            logger.error(f"Error obteniendo info del volumen: {e}")
            return (64, 64, 64), (0, 0, 0), (3.0, 3.0, 3.0)

    def _get_phantom_labelmap(self, segmentation_node, dims) -> Optional[np.ndarray]:
        """
        Extrae el labelmap del phantom desde el segmentation node.

        El segmentation node del phantom contiene los indices 1,30,50,80,90,100.
        """
        import slicer
        from vtk.util import numpy_support

        try:
            # Exportar segmentation a labelmap temporal
            labelmap_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", "__mcnp_phantom__"
            )
            slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
                segmentation_node, labelmap_node
            )

            # Extraer array numpy
            img_data = labelmap_node.GetImageData()
            arr = numpy_support.vtk_to_array(img_data).astype(np.uint8)

            # Ajustar dimensiones si es necesario
            vtk_dims = img_data.GetDimensions()
            if arr.ndim == 3:
                if arr.shape[0] == vtk_dims[2]:  # (z, y, x)
                    arr = arr.transpose(2, 1, 0)

            slicer.mrmlScene.RemoveNode(labelmap_node)
            return arr

        except Exception as e:
            logger.error(f"Error extrayendo phantom labelmap: {e}")
            return None

    def _get_hu_array(self, ct_volume_node, dims) -> np.ndarray:
        """Extrae array de HU del CT."""
        import slicer
        from vtk.util import numpy_support

        try:
            img_data = ct_volume_node.GetImageData()
            arr = numpy_support.vtk_to_array(img_data).astype(np.int16)
            if arr.ndim == 3:
                vtk_dims = img_data.GetDimensions()
                if arr.shape[0] == vtk_dims[2]:
                    arr = arr.transpose(2, 1, 0)
            return arr
        except Exception as e:
            logger.warning(f"Error extrayendo HU array: {e}")
            return np.zeros(dims, dtype=np.int16)

    def _write_input(
        self,
        path: str,
        iso_data: dict,
        n_particles: int,
        dens_cards: list[str],
        mat_cards: list[str],
        geom_cards: list[str],
        src_cards: list[str],
        tal_cards: list[str],
    ):
        """Escribe el archivo de entrada MCNP formateado."""
        lines = []
        lines.append(f"3Dosim MCNP input - {iso_data['name']}")
        lines.append(f"C Generado por SlicerDosim")
        lines.append(f"C Isotopo: {iso_data['name']} (ZAID={iso_data['zaid']})")
        lines.append(f"C Particulas: {n_particles}")
        lines.append(f"C")
        lines.append(f"C ========================================================")
        lines.append(f"C TARJETAS DE DENSIDAD")
        lines.append(f"C ========================================================")
        lines.extend(dens_cards)
        lines.append(f"C")
        lines.append(f"C ========================================================")
        lines.append(f"C TARJETAS DE MATERIAL")
        lines.append(f"C ========================================================")
        lines.extend(mat_cards)
        lines.append(f"C")
        lines.append(f"C ========================================================")
        lines.append(f"C CELDAS Y SUPERFICIES")
        lines.append(f"C ========================================================")
        lines.extend(geom_cards)
        lines.append(f"C")
        lines.append(f"C ========================================================")
        lines.append(f"C DEFINICION DE FUENTE")
        lines.append(f"C ========================================================")
        lines.extend(src_cards)
        lines.append(f"C")
        lines.append(f"C ========================================================")
        lines.append(f"C TALLIES, CORTE, NPS")
        lines.append(f"C ========================================================")
        lines.extend(tal_cards)

        with open(path, "w") as f:
            f.write("\n".join(lines))
            f.write("\n")

    # ------------------------------------------------------------------
    # METODOS LEGACY (mantener compatibilidad)
    # ------------------------------------------------------------------

    def generate_check_register(self, patient_data: dict) -> str:
        """Genera archivo MCNP para verificar registro."""
        return ""

    def generate_validation_mird(self, sphere_diam_mm: float = 30.0) -> str:
        """Genera archivo MCNP para validacion MIRD."""
        return ""
