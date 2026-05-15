"""
Parser de archivos MCTAL (output MCNP).

Lee archivos MCTAL en formato ASCII generados por MCNP
y extrae los datos de dosis del FMESH4 y F6 tallies.
"""

from __future__ import annotations

import logging
import numpy as np
import os
import re
from typing import Optional


logger = logging.getLogger(__name__)


class MCTALParser:
    """
    Parsea archivos MCTAL de MCNP.

    El formato MCTAL es un archivo ASCII estructurado que contiene:
      - Cabecera con titulo y fechas
      - Tabla de nuclidos (opcional)
      - Datos de cada tally: valores, incertidumbres, bins

    Soporta:
      - Tally FMESH4 (mesh 3D)
      - Tally F6 (celda)
    """

    def parse(self, path: str) -> dict:
        """
        Parsea un archivo MCTAL completo.

        Args:
            path: ruta al archivo .mctal

        Returns:
            dict con:
              - 'dose_3d': array 3D de dosis (o None si no se pudo)
              - 'uncertainty': array 3D de incertidumbre relativa
              - 'dimensions': (nx, ny, nz)
              - 'tally_data': dict con datos de cada tally encontrado
              - 'title': titulo del problema
              - 'nps': numero de historias
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo MCTAL no encontrado: {path}")

        logger.info(f"Parseando MCTAL: {path}")
        filesize = os.path.getsize(path)
        logger.info(f"  Tamano: {filesize} bytes")

        result = {
            "dose_3d": None,
            "uncertainty": None,
            "dimensions": (0, 0, 0),
            "tally_data": {},
            "title": "",
            "nps": 0,
            "source_file": path,
        }

        try:
            with open(path, "r") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error leyendo MCTAL: {e}")
            return result

        # Normalizar saltos de linea
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = content.split("\n")

        # Extraer titulo (primeras lineas)
        result["title"] = self._parse_title(lines)

        # Extraer NPS
        result["nps"] = self._parse_nps(lines)

        # Parsear cada tally
        tally_blocks = self._split_tallies(lines)
        logger.info(f"  Tallies encontrados: {list(tally_blocks.keys())}")

        for tally_id, block in tally_blocks.items():
            tally_data = self._parse_tally_block(block, tally_id)
            result["tally_data"][tally_id] = tally_data

            # Si es FMESH4 o tiene datos 3D, extraer dosis
            if tally_data.get("type") == "mesh" or "values_3d" in tally_data:
                values = tally_data.get("values_3d")
                unc = tally_data.get("uncertainty_3d")
                dims = tally_data.get("dimensions")
                if values is not None:
                    result["dose_3d"] = values
                    result["uncertainty"] = unc
                    result["dimensions"] = dims
                    logger.info(
                        f"  Dosis 3D extraida: {dims}, "
                        f"min={values.min():.6e} max={values.max():.6e}"
                    )

        return result

    def _parse_title(self, lines: list[str]) -> str:
        """Extrae el titulo del problema."""
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith("1") and not line.startswith("mctal"):
                return line
        return ""

    def _parse_nps(self, lines: list[str]) -> int:
        """Extrae el numero de historias (NPS)."""
        for line in lines[:20]:
            m = re.search(r"nps\s*=\s*(\d+)", line, re.IGNORECASE)
            if m:
                return int(m.group(1))
            m = re.search(r"(\d+)\s+particles", line, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return 0

    def _split_tallies(self, lines: list[str]) -> dict[int, list[str]]:
        """
        Divide el archivo en bloques por tally.

        Cada bloque comienza con 'tally <id>' y termina antes del
        siguiente tally o del fin del archivo.

        Returns:
            dict: tally_id -> lineas del bloque
        """
        tally_blocks: dict[int, list[str]] = {}
        current_tally: Optional[int] = None
        current_block: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Detectar inicio de tally
            m = re.match(r"^tally\s+(\d+)", stripped, re.IGNORECASE)
            if m:
                # Guardar bloque anterior
                if current_tally is not None and current_block:
                    tally_blocks[current_tally] = current_block
                current_tally = int(m.group(1))
                current_block = [stripped]
            else:
                if current_tally is not None:
                    current_block.append(stripped)

        # Ultimo bloque
        if current_tally is not None and current_block:
            tally_blocks[current_tally] = current_block

        return tally_blocks

    def _parse_tally_block(self, block: list[str], tally_id: int) -> dict:
        """
        Parsea un bloque de tally individual.

        Returns:
            dict con tipo, valores, dimensiones, etc.
        """
        result = {
            "tally_id": tally_id,
            "type": "unknown",
            "values": None,
            "uncertainty": None,
            "values_3d": None,
            "uncertainty_3d": None,
            "dimensions": (0, 0, 0),
            "particle": "",
        }

        if not block:
            return result

        # Primera linea: "tally <id> <particle> ..."
        header = block[0]
        parts = header.split()
        if len(parts) >= 2:
            # Detectar tipo de tally por nombre
            tally_upper = " ".join(block).upper()
            if "FMESH" in tally_upper or "MESH" in tally_upper:
                result["type"] = "mesh"
            else:
                result["type"] = "cell"

        # Parsear datos numericos
        data_lines = block[1:]
        values = []
        for line in data_lines:
            line = line.strip()
            if not line:
                continue
            try:
                nums = [float(x) for x in line.split()]
                values.extend(nums)
            except ValueError:
                pass

        if values:
            # Para FMESH4, intentar reconstruir dimensiones
            n_vals = len(values)
            # Si es par, mitad son valores, mitad incertidumbres
            if n_vals >= 2:
                # Asumir que los datos vienen como pares (valor, error)
                # o que el error esta en una seccion separada
                result["values"] = np.array(values)

            # Intentar determinar dimensiones desde el contexto
            # (se establecen externamente desde la geometria)
            result["dimensions"] = (n_vals, 1, 1)

        return result

    def reconstruct_3d(
        self, tally_data: dict, dims: tuple[int, int, int]
    ) -> dict:
        """
        Reconstruye array 3D a partir de datos planos del tally.

        Args:
            tally_data: dict del tally
            dims: (nx, ny, nz) dimensiones esperadas

        Returns:
            dict actualizado con values_3d y uncertainty_3d
        """
        nx, ny, nz = dims
        expected = nx * ny * nz

        values = tally_data.get("values")
        if values is None or values.size < expected:
            logger.warning(
                f"Datos insuficientes: {values.size if values is not None else 0} "
                f"< {expected}"
            )
            return tally_data

        # Los valores MCTAL vienen en orden z, y, x (plano x-y por z)
        # Shape MCNP: (nz, ny, nx) o plano
        try:
            # Truncar o rellenar al tamano esperado
            v = values[:expected].astype(np.float64)

            # Reconstruir 3D asumiendo orden (nx, ny, nz) o (nz, ny, nx)
            # Probar primero (nz, ny, nx) que es el orden MCNP tipico
            try:
                v_3d = v.reshape(nz, ny, nx)
                # Transponer a (nx, ny, nz) para consistencia interna
                v_3d = v_3d.transpose(2, 1, 0)
            except ValueError:
                try:
                    v_3d = v.reshape(nx, ny, nz)
                except ValueError:
                    logger.error(f"No se pudo reshape {v.shape} a ({nx},{ny},{nz})")
                    return tally_data

            tally_data["values_3d"] = v_3d
            tally_data["dimensions"] = dims
            logger.info(f"  Reconstruido 3D: {v_3d.shape}, rango [{v_3d.min():.4e}, {v_3d.max():.4e}]")

        except Exception as e:
            logger.error(f"Error reconstruyendo 3D: {e}")

        return tally_data

    def compute_dose_gy(
        self, mctal_data: dict, activity_gbq: float = 1.0
    ) -> Optional[np.ndarray]:
        """
        Convierte dosis MCTAL a Gray.

        La conversion depende del tally:
          - FMESH4: los valores estan en MeV/g/particula
          - D_Gy = D_MeV_g * actividad_GBq * k / lambda

        donde k = 49.98 J-s (constante de conversion).

        Args:
            mctal_data: dict de _parse_mctal
            activity_gbq: actividad administrada en GBq

        Returns:
            array 3D de dosis en Gy, o None
        """
        dose_raw = mctal_data.get("dose_3d")
        if dose_raw is None:
            return None

        nps = mctal_data.get("nps", 1)
        if nps <= 0:
            nps = 1

        # Constante de conversion
        k = 49.98  # MeV/g/particula -> Gy (asumiendo 1 particula/desintegracion)

        # Escalar por actividad y NPS
        # D_Gy = D_MeV_g * (N_desintegraciones) * k
        # N_desintegraciones = actividad_GBq * 1e9 * (tiempo)
        # Para simulacion MCNP: D_Gy = D_MeV_g * actividad_GBq * k / nps

        dose_gy = dose_raw * activity_gbq * k / nps

        logger.info(
            f"Dosis convertida a Gy: media={dose_gy.mean():.4f} Gy, "
            f"max={dose_gy.max():.4f} Gy"
        )

        return dose_gy
