"""
Generador de archivos de entrada MCNP para SlicerDosim.

Formato MATLAB de referencia: 3Dosim_MCNP_Y90_universos.i
- Universos con LIKE n BUT, sphere 650 como boundary
- Lattice fill con RLE
- Fuente desde archivo .src externo (Y90cel3D.src)
- Talles TMESH
- Materiales: aire (m1) + tejido blando (m2) para todos los organos
"""

from __future__ import annotations

import logging
import os
import numpy as np
from typing import Optional

from .config import TissueConfig


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MAPPING: TotalSegmentator segment names -> phantom indices
# ---------------------------------------------------------------------------
# 1 = Aire (reservado)
# 2-25 = Organos individuales de TS (mat=2 tejido blando)
# 30 = Soft Tissue general (mat=2)
# 50 = Lung - todos los lobulos (mat=2)
# 80 = Bone - vertebras, costillas, escapula, esternon (mat=2)
# 90 = Liver (mat=2)
# 100 = Tumor (mat=2)
#
# Los indices 90 (liver) y 100 (tumor) se mantienen del tissue_config original.
# Todos los organos usan material 2 (tejido blando ICRU 44) por ahora.
# ---------------------------------------------------------------------------

TS_SEGMENT_MAP = {
    "spleen": 2,
    "right kidney": 3,
    "left kidney": 4,
    "gallbladder": 5,
    "liver": 90,            # MANTENER indice existente
    "stomach": 6,
    "pancreas": 7,
    "right adrenal gland": 8,
    "left adrenal gland": 9,
    "superior lobe of left lung": 50,   # MANTENER lung group
    "inferior lobe of left lung": 50,
    "superior lobe of right lung": 50,
    "middle lobe of right lung": 50,
    "inferior lobe of right lung": 50,
    "esophagus": 10,
    "small bowel": 11,
    "duodenum": 12,
    "colon": 13,
    "heart": 14,
    "aorta": 15,
    "pulmonary venous system": 16,
    "left atrial appendage": 17,
    "superior vena cava": 18,
    "inferior vena cava": 19,
    "portal vein and splenic vein": 20,
    "spinal cord": 21,
    "left deep back muscle": 22,
    "right deep back muscle": 23,
    "left iliopsoas muscle": 24,
    "right iliopsoas muscle": 25,
    # Vertebrae -> bone group
    "l3 vertebra": 80,
    "l2 vertebra": 80,
    "l1 vertebra": 80,
    "t12 vertebra": 80,
    "t11 vertebra": 80,
    "t10 vertebra": 80,
    "t9 vertebra": 80,
    "t8 vertebra": 80,
    "t7 vertebra": 80,
    "t6 vertebra": 80,
    # Scapulae -> bone group
    "left scapula": 80,
    "right scapula": 80,
    # Ribs -> bone group
    "left rib 3": 80,
    "left rib 4": 80,
    "left rib 5": 80,
    "left rib 6": 80,
    "left rib 7": 80,
    "left rib 8": 80,
    "left rib 9": 80,
    "left rib 10": 80,
    "left rib 11": 80,
    "left rib 12": 80,
    "right rib 3": 80,
    "right rib 4": 80,
    "right rib 5": 80,
    "right rib 6": 80,
    "right rib 7": 80,
    "right rib 8": 80,
    "right rib 9": 80,
    "right rib 10": 80,
    "right rib 11": 80,
    "right rib 12": 80,
    "sternum": 80,
    "costal cartilage": 80,
    # Tumor (synthetic)
    "tumor": 100,
    "tumor_sintetico": 100,
}

# Phantom index -> MCNP material info (solo 2 materiales)
PHANTOM_MAT_MAP = {
    1:   {"mid": 1, "name": "Aire Dry (near sea level)", "rho": 0.001205},
    # Todos los organos -> mat 2 (tejido blando)
    2:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    3:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    4:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    5:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    6:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    7:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    8:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    9:   {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    10:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    11:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    12:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    13:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    14:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    15:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    16:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    17:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    18:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    19:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    20:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    21:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    22:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    23:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    24:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    25:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    30:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    50:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    80:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    90:  {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
    100: {"mid": 2, "name": "Soft Tissue (ICRU 44)", "rho": 1.06},
}

# Composiciones MCNP: (ZAID, weight_fraction negativa = mass fraction)
MAT_COMPOSITIONS = {
    1: [  # Aire Dry (near sea level)
        (6000,  -0.000124),
        (7000,  -0.755268),
        (8000,  -0.231481),
        (18000, -0.012827),
    ],
    2: [  # Soft Tissue (ICRU 44)
        (1000,  -0.105),
        (6000,  -0.143),
        (7000,  -0.034),
        (8000,  -0.708),
        (11000, -0.002),
        (15000, -0.003),
        (16000, -0.003),
        (17000, -0.002),
        (19000, -0.003),
    ],
}


class MCNPInputGenerator:
    """
    Generador de entrada MCNP siguiendo el formato MATLAB de 3Dosim.

    Produce un archivo .i con:
      - Universos (LIKE n BUT) con sphere 650 como boundary
      - Lattice voxelizado con RLE
      - Fuente desde archivo .src externo
      - Talles TMESH
      - Materiales: m1 (aire) + m2 (tejido blando)
    """

    def __init__(self):
        self.config = TissueConfig()

    # ======================================================================
    # PUBLIC API
    # ======================================================================

    def generate(
        self,
        ct_volume_node,
        pet_volume_node=None,
        segmentation_node=None,
        output_dir: str = ".",
        isotope: str = "Y-90",
        n_particles: int = int(1e7),
        refine_hu: bool = False,
        flip_rows: bool = False,
    ) -> str:
        """
        Genera archivo de entrada MCNP completo.

        Args:
            ct_volume_node: vtkMRMLScalarVolumeNode del CT
            pet_volume_node: vtkMRMLScalarVolumeNode del PET (opcional)
            segmentation_node: vtkMRMLLabelMapVolumeNode o vtkMRMLSegmentationNode
            output_dir: directorio de salida
            isotope: isotopo (Y-90, I-131, Lu-177, Tc-99m)
            n_particles: numero de historias
            refine_hu: si True, refina materiales por HU (no usado por ahora)
            flip_rows: si True, invierte eje Y antes de RLE (como MATLAB)

        Returns:
            ruta al archivo .i generado
        """
        iso_data = ISOTOPE_DATA.get(isotope)
        if iso_data is None:
            raise ValueError(f"Isotopo no soportado: {isotope}")

        logger.info(f"Generando entrada MCNP para {isotope}, {n_particles} particulas")
        logger.info(f"  CT: {ct_volume_node.GetName() if ct_volume_node else 'None'}")
        logger.info(f"  PET: {pet_volume_node.GetName() if pet_volume_node else 'None'}")

        # 1. Extraer info del volumen
        dims, origin, spacing = self._get_volume_info(ct_volume_node)
        nx, ny, nz = dims
        logger.info(f"  Dimensiones (voxeles): {dims}")
        logger.info(f"  Espaciado (mm): {spacing}")
        logger.info(f"  Dimensiones (cm): {nx*spacing[0]/10:.2f} x {ny*spacing[1]/10:.2f} x {nz*spacing[2]/10:.2f}")

        # 2. Extraer labelmap
        self._ct_ref_node = ct_volume_node
        phantom_arr = self._get_phantom_labelmap(segmentation_node, dims)
        if phantom_arr is None:
            raise RuntimeError("No se pudo extraer labelmap del phantom")
        unique_vals = sorted(np.unique(phantom_arr))
        logger.info(f"  Indices phantom: {unique_vals}")

        # 3. Extraer PET array
        pet_arr = self._get_pet_array(pet_volume_node, dims)

        # 4. Escribir archivo MCNP
        os.makedirs(output_dir, exist_ok=True)
        input_path = os.path.join(output_dir, "3Dosim_mcnp.i")

        with open(input_path, "w") as f:
            self._write_header(f, isotope, iso_data)
            self._write_universes(f, phantom_arr, dims, spacing)
            self._write_lattice(f, phantom_arr, dims, spacing, flip_rows)
            self._write_surfaces(f, dims, spacing)
            self._write_mode(f, iso_data)
            self._write_source(f, pet_arr, dims, spacing, phantom_arr, iso_data)
            self._write_tallies(f, dims, spacing, iso_data)
            self._write_materials(f)
            self._write_footer(f, n_particles)

        file_size_mb = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"Archivo MCNP generado: {input_path} ({file_size_mb:.1f} MB)")
        return input_path

    # ======================================================================
    # HELPERS DE EXTRACCION
    # ======================================================================

    def _get_volume_info(self, volume_node):
        """Obtiene (dimensions, origin, spacing) de un volumen VTK."""
        try:
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
        Extrae labelmap 3D numpy del phantom.

        Mapea cada segmento de TotalSegmentator a su indice phantom
        usando TS_SEGMENT_MAP. Los indices 90 (liver) y 100 (tumor)
        se mantienen del tissue_config original.
        """
        import slicer
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy

        try:
            logger.info(f"  Extrayendo labelmap de: {segmentation_node.GetName()}")

            # --- Caso 1: ya es labelmap ---
            if segmentation_node.IsA("vtkMRMLLabelMapVolumeNode"):
                logger.info("  Nodo es labelmap, usando directo")
                img_data = segmentation_node.GetImageData()
                if img_data is None:
                    logger.error("  GetImageData() devolvio None")
                    return None

                scalars = img_data.GetPointData().GetScalars()
                if scalars is None:
                    scalars = img_data.GetCellData().GetScalars()
                if scalars is None:
                    logger.error("  No se encontraron escalares en labelmap")
                    return None

                arr_flat = vtk_to_numpy(scalars)
                vtk_dims = img_data.GetDimensions()
                arr = arr_flat.reshape((vtk_dims[2], vtk_dims[1], vtk_dims[0]))
                arr = arr.transpose(2, 1, 0)
                logger.info(f"  Array shape: {arr.shape} (X,Y,Z)")
                logger.info(f"  Valores unicos: {np.unique(arr)}")
                return arr

            # --- Caso 2: segmentation node ---
            seg_ids = vtk.vtkStringArray()
            segmentation_node.GetSegmentation().GetSegmentIDs(seg_ids)
            n_segments = seg_ids.GetNumberOfValues()
            logger.info(f"  Segmentos disponibles: {n_segments}")
            if n_segments == 0:
                logger.error("  La segmentacion no tiene segmentos")
                return None

            # Crear array acumulado con todos los segmentos
            nx, ny, nz = dims
            accumulated = np.zeros((nx, ny, nz), dtype=np.int32)

            # Referencia geometrica: CT node
            ref_node = getattr(self, '_ct_ref_node', None)
            if ref_node is None:
                ref_node = segmentation_node

            tmp_labelmap = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", "__mcnp_phantom__"
            )

            exported_count = 0
            for i in range(n_segments):
                seg_id = seg_ids.GetValue(i)
                segment = segmentation_node.GetSegmentation().GetSegment(seg_id)
                seg_name = segment.GetName() if segment else seg_id

                # Buscar indice phantom para este segmento
                # Buscar por nombre (case-insensitive)
                seg_name_lower = seg_name.lower().replace(" ", " ").strip()
                phantom_idx = None
                for ts_name, idx in TS_SEGMENT_MAP.items():
                    if ts_name.lower() == seg_name_lower:
                        phantom_idx = idx
                        break

                if phantom_idx is None:
                    logger.debug(f"  Segmento '{seg_name}' no mapeado, saltando")
                    continue

                # Exportar este segmento como mascara binaria
                single_ids = vtk.vtkStringArray()
                single_ids.InsertNextValue(seg_id)
                slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
                    segmentation_node, single_ids, tmp_labelmap, ref_node
                )

                tmp_img = tmp_labelmap.GetImageData()
                if tmp_img is None or tmp_img.GetPointData().GetScalars() is None:
                    continue

                seg_scalars = vtk_to_numpy(tmp_img.GetPointData().GetScalars())
                if seg_scalars is None:
                    continue

                vtk_d = tmp_img.GetDimensions()
                seg_arr = seg_scalars.reshape((vtk_d[2], vtk_d[1], vtk_d[0])).transpose(2, 1, 0)

                # Acumular: donde la mascara es > 0, poner el phantom_idx
                # Prioridad: indice mas alto gana (tumor=100 > liver=90 > bone=80 > ...)
                mask = seg_arr > 0
                if phantom_idx > 0:
                    overwrite = mask & ((accumulated == 0) | (phantom_idx > accumulated))
                    accumulated[overwrite] = phantom_idx
                    exported_count += 1
                    logger.debug(f"  Segmento '{seg_name}': {mask.sum()} voxels -> idx {phantom_idx}")

            # Limpiar
            slicer.mrmlScene.RemoveNode(tmp_labelmap)

            # Convertir 0 (vacio) -> 1 (aire)
            accumulated[accumulated == 0] = 1

            unique_vals = sorted(np.unique(accumulated))
            logger.info(f"  Exportados {exported_count}/{n_segments} segmentos")
            logger.info(f"  Indices phantom: {unique_vals}")
            logger.info(f"  Array shape: {accumulated.shape} (X,Y,Z)")

            if exported_count == 0:
                logger.error("  No se pudo exportar ningun segmento")
                return None

            return accumulated

        except Exception as e:
            logger.error(f"Error extrayendo phantom labelmap: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_pet_array(self, pet_volume_node, dims) -> Optional[np.ndarray]:
        """Extrae array 3D del PET."""
        if pet_volume_node is None:
            return None
        try:
            from vtk.util.numpy_support import vtk_to_numpy
            img_data = pet_volume_node.GetImageData()
            if img_data is None:
                return None
            arr = vtk_to_numpy(img_data.GetPointData().GetScalars())
            if arr is None:
                return None
            vtk_dims = img_data.GetDimensions()
            try:
                arr = arr.reshape((vtk_dims[2], vtk_dims[1], vtk_dims[0]))
                arr = arr.transpose(2, 1, 0)
            except ValueError:
                arr = arr.reshape(dims)
            logger.info(f"  PET array shape: {arr.shape}")
            return arr.astype(np.float64)
        except Exception as e:
            logger.warning(f"No se pudo extraer PET: {e}")
            return None

    # ======================================================================
    # ESCRITURA DEL ARCHIVO MCNP (formato MATLAB)
    # ======================================================================

    def _write_header(self, f, isotope, iso_data):
        """Escribe cabecera del archivo."""
        import datetime
        now = datetime.datetime.now()
        f.write("c ------------------------------------------------------ \n")
        f.write("c ------------------------------------------------------ \n")
        f.write("c ------------------------------------------------------ \n")
        f.write("c Archivo generado con 3Dosim, version 3.14 \n")
        f.write(f"c Fecha : {now.strftime('%d-%b-%Y %H:%M')} hs \n")
        f.write("c ------------------------------------------------------  \n")
        f.write("c ------------------------------------------------------  \n")
        f.write("c ------------------------------------------------------  \n")
        f.write("c   \n")
        f.write("c Universos \n")

    def _write_universes(self, f, phantom_arr, dims, spacing):
        """
        Escribe universos MCNP.
        Universo 1 = aire (referencia para LIKE n BUT).
        Todos los demas = like 1 but mat=2 rho=-1.06.
        SIN closure cells.
        """
        unique_vals = sorted(set(phantom_arr.flatten()))
        unique_vals = [v for v in unique_vals if v > 0]

        logger.info(f"  Universos a generar: {unique_vals}")

        # Universo 1 = aire (referencia)
        f.write("1 1 -0.001205 -650 u=1 imp:p=1 imp:e=1 $ Aire\n")

        # Demas universos: like 1 but mat=2 rho=-1.06
        for v in unique_vals:
            if v == 1:
                continue  # ya escrito
            # Buscar nombre del segmento
            seg_name = self._get_segment_name(v)
            f.write(f"{v} like 1 but mat=2 rho=-1.06 u={v} imp:p=1 imp:e=1 $ {seg_name}\n")

    def _get_segment_name(self, phantom_idx):
        """Retorna el nombre del segmento para un indice phantom."""
        for name, idx in TS_SEGMENT_MAP.items():
            if idx == phantom_idx:
                return name
        return f"idx_{phantom_idx}"

    def _write_lattice(self, f, phantom_arr, dims, spacing, flip_rows=False):
        """
        Escribe lattice wrapper + fill data con RLE.
        Cell 101 = fill wrapper, Cell 102 = lattice.
        SIN closure cells.
        """
        nx, ny, nz = dims

        # Lattice wrapper cells
        f.write("101 0 -1 fill=101 imp:p=1 imp:e=1\n")
        f.write("102 0 -2 lat=1 u=101 imp:p=1 imp:e=1\n")
        f.write(f"                              fill=0:{nx-1} 0:{ny-1} 0:{nz-1} \n")

        # Fill data con RLE
        self._write_rle_fill(f, phantom_arr, nx, ny, nz, flip_rows)

        # Outside world cell
        f.write("9999 0 1 imp:p=0 imp:e=0\n")
        f.write("\n")

    def _write_rle_fill(self, f, phantom_arr, nx, ny, nz, flip_rows=False):
        """
        Escribe fill de voxeles con RLE estilo MATLAB.
        """
        if flip_rows:
            phantom_arr = phantom_arr[:, ::-1, :]
            logger.info("  Flip Y aplicado antes de RLE")

        col = 0
        line = "      "  # 6 espacios de indentacion

        def flush_run(r_val):
            nonlocal col, line
            if r_val >= 1:
                if r_val == 1:
                    token = " r"
                else:
                    token = f" {r_val}r"
                if col + len(token) > 72:
                    f.write(line.rstrip() + "\n")
                    line = "      "
                    col = 6
                line += token
                col += len(token)

        def write_val(val):
            nonlocal col, line
            token = f" {val}"
            if col + len(token) > 72:
                f.write(line.rstrip() + "\n")
                line = "      "
                col = 6
            line += token
            col += len(token)

        # Primer elemento fuera del loop
        first_val = int(phantom_arr[0, 0, 0])
        if first_val == 0:
            first_val = 1
        write_val(first_val)

        prev_val = first_val
        r = -1

        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    val = int(phantom_arr[i, j, k])
                    if val == 0:
                        val = 1  # fuera del cuerpo = aire
                    if val == prev_val:
                        r += 1
                    else:
                        flush_run(r)
                        write_val(val)
                        r = 0
                    prev_val = val

        flush_run(r)
        f.write(line.rstrip() + "\n")

    def _write_surfaces(self, f, dims, spacing):
        """Escribe superficies: RPP bounding box + RPP voxel + SO 650 sphere."""
        nx, ny, nz = dims
        sx, sy, sz = spacing  # mm
        sx_cm = round(sx / 10.0, 4)
        sy_cm = round(sy / 10.0, 4)
        sz_cm = round(sz / 10.0, 4)
        xm = round(nx * sx_cm, 4)
        ym = round(ny * sy_cm, 4)
        zm = round(nz * sz_cm, 4)

        f.write("\n")
        f.write("c Superficies \n")
        f.write(f"c Tamano del voxel:  dx= {sx_cm} dy= {sy_cm} dz= {sz_cm} \n")
        f.write(f"c Tamano de la imagen:  [ {nx} {ny} {nz} ] \n")
        f.write("c\n")
        f.write(f"1   rpp  0.  {xm} 0.  {ym} 0.  {zm} \n")
        f.write(f"2   rpp  0.  {sx_cm} 0. {sy_cm} 0. {sz_cm} \n")
        f.write("650 so 15 \n")
        f.write("\n")

    def _write_mode(self, f, iso_data):
        """Escribe tarjetas de modo, phys y cut."""
        e_max = iso_data.get("e_max", 2.28)
        f.write("c\n")
        f.write("c MODDE \n")
        f.write("mode e p\n")
        f.write(f"phys:p {e_max} J J J J J J\n")
        f.write(f"phys:e {e_max} J J J J J J J J J J J J 0.99\n")
        f.write("cut:p J 1e-3\n")
        f.write("cut:e J 1e-3\n")

    def _write_source(self, f, pet_arr, dims, spacing, phantom_arr, iso_data):
        """
        Escribe fuente MCNP.
        SDEF con read file Y90cel3D.src + distribucion voxel si5/sp5.
        """
        nx, ny, nz = dims
        sx, sy, sz = spacing  # mm
        sx_cm = round(sx / 10.0, 4)
        sy_cm = round(sy / 10.0, 4)
        sz_cm = round(sz / 10.0, 4)

        # Determinar mascara de fuente: todos los voxeles no-aire
        non_air_mask = phantom_arr > 0

        if pet_arr is not None and pet_arr.sum() > 0:
            source_arr = pet_arr * non_air_mask
            active_idx = np.where((source_arr > 0) & non_air_mask)
            n_active = len(active_idx[0])

            if n_active == 0:
                logger.warning("No hay actividad PET, usando fuente uniforme")
                active_idx = np.where(non_air_mask)
                n_active = len(active_idx[0])
        else:
            active_idx = np.where(non_air_mask)
            n_active = len(active_idx[0])

        logger.info(f"  Fuente: {n_active} voxeles activos")

        f.write("\n")
        f.write("c FUENTE \n")
        f.write("c sdef erg d1 x d2 y d3 z d4 cell d5  par e \n")
        f.write("sdef par=d1 wgt=1.00033788800193 erg=fpar=d6 x=d2 y=d3 z=d4 cell=d5\n")
        f.write("c\n")
        f.write("read file Y90cel3D.src\n")
        f.write("c\n")

        # Distribucion en el voxel
        f.write("c Distribucion en el voxel\n")
        f.write("c\n")
        f.write(f"si2 h 0. {sx_cm}\n")
        f.write("sp2 d 0 1\n")
        f.write(f"si3 h 0. {sy_cm}\n")
        f.write("sp3 d 0 1\n")
        f.write(f"si4 h 0. {sz_cm}\n")
        f.write("sp4 d 0 1\n")

        # Voxeles fuente (si5)
        f.write("c Voxeles Fuente\n")
        f.write("si5 l")
        col = 6
        line = ""
        for n in range(n_active):
            ix = active_idx[0][n]
            iy = active_idx[1][n]
            iz = active_idx[2][n]
            val = int(phantom_arr[ix, iy, iz])
            # Formato: (mat_id <102[ ix iy iz ]<101)
            token = f" ({val}<102[{ix} {iy} {iz}]<101)"
            if col + len(token) > 72:
                f.write(line + "\n")
                f.write("      ")
                line = token
                col = 6 + len(token)
            else:
                line += token
                col += len(token)
        f.write(line + "\n")

        # Pesos uniformes
        f.write("sp5")
        col = 4
        line = ""
        w = 1.0 / n_active if n_active > 0 else 1.0
        for n in range(n_active):
            token = f" {w:.12e}"
            if col + len(token) > 72:
                f.write(line + "\n")
                f.write("     ")
                line = token
                col = 5 + len(token)
            else:
                line += token
                col += len(token)
        f.write(line + "\n")

        f.write(f"c Se generaron N fuentes: {n_active}\n")

    def _write_tallies(self, f, dims, spacing, iso_data):
        """Escribe talles TMESH."""
        nx, ny, nz = dims
        sx, sy, sz = spacing  # mm
        xm = round(nx * sx / 10.0, 4)
        ym = round(ny * sy / 10.0, 4)
        zm = round(nz * sz / 10.0, 4)

        f.write("\n")
        f.write("c\n")
        f.write("c TALLY \n")
        f.write("c Tally de verificacion \n")
        f.write("c\n")
        f.write("c MESH TALLY 1=F6 \n")
        f.write("c MeV/(cm^3 source_particle) \n")
        f.write("tmesh \n")
        f.write("c \n")
        f.write("rmesh1:e   pedep \n")
        f.write(f"cora1  0  {nx-1}i   {xm} \n")
        f.write(f"corb1  0  {ny-1}i   {ym} \n")
        f.write(f"corc1  0  {nz-1}i   {zm} \n")
        f.write("c\n")
        f.write("endmd \n")
        f.write("\n")

    def _write_materials(self, f):
        """Escribe tarjetas de materiales MCNP: m1 (aire) + m2 (tejido blando)."""
        f.write("c \n")
        f.write("c MATERIALES\n")

        # m1 = Aire
        f.write("c Aire Dry (near sea level)\n")
        f.write("c densidad [g/cm^3]:   0.001205 \n")
        f.write("c suma de composicion:   0.9997 \n")
        for mid, comp in MAT_COMPOSITIONS.items():
            f.write(f"m{mid}")
            for z, frac in comp:
                f.write(f"          {z}            {frac} \n")
            f.write("\n")

    def _write_footer(self, f, n_particles):
        """Escribe RAND, DBCN, PRINT, PRDMP, NPS."""
        import random
        seed = random.randint(1, 99999999999999)
        stride = 1111152917

        f.write("c\n")
        f.write("c RAND \n")
        f.write(f"rand stride={stride} gen=2 seed= {seed} \n")
        f.write("c DBCN \n")
        f.write("dbcn 48j 1 \n")
        f.write("c \n")
        f.write("c PRINT \n")
        f.write("print -85 -86 -128\n")
        f.write("c PRDMP \n")
        f.write("PRDMP J 1e4 -1 1 1e4\n")
        f.write(f"NPS {n_particles} \n")


# Isotope data for source
ISOTOPE_DATA = {
    "Y-90": {
        "name": "Yttrium-90",
        "zaid": 39090,
        "half_life_days": 2.67,
        "e_max": 2.2807,
        "particle": "e",
        "mode": "e p",
    },
    "I-131": {
        "name": "Iodine-131",
        "zaid": 53131,
        "half_life_days": 8.02,
        "e_max": 0.606,
        "particle": "e",
        "mode": "e",
    },
    "Lu-177": {
        "name": "Lutetium-177",
        "zaid": 77177,
        "half_life_days": 6.65,
        "e_max": 0.498,
        "particle": "e",
        "mode": "e",
    },
    "Tc-99m": {
        "name": "Technetium-99m",
        "zaid": 43099,
        "half_life_days": 0.25,
        "e_max": 0.140,
        "particle": "p",
        "mode": "p e",
    },
}
