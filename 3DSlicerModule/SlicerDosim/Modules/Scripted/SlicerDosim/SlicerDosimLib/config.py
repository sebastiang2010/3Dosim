"""
Cargador de configuracion de tejidos para el phantom 3Dosim.

Lee tissue_config.json y provee acceso tipado a:
  - Indices, nombres, colores de cada tejido
  - Composiciones MCNP (material cards)
  - Mapping TotalSegmentator → phantom
  - Labels de cuerpo para tejido blando
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional


logger = logging.getLogger(__name__)


def _find_config_path() -> str:
    """
    Busca tissue_config.json relativo a la ubicacion de este modulo.
    Orden de busqueda:
      1. Junto a este archivo (./)
      2. ../../Resources/Config/ (estructura tipica Slicer)
      3. Variable de entorno 3DOSIM_TISSUE_CONFIG
    """
    # 1. Junto a config.py
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(this_dir, "tissue_config.json"),
        os.path.join(this_dir, "..", "Resources", "Config", "tissue_config.json"),
        os.path.join(this_dir, "..", "..", "Resources", "Config", "tissue_config.json"),
        os.environ.get("3DOSIM_TISSUE_CONFIG", ""),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError(
        "tissue_config.json no encontrado. Buscado en: " + ", ".join(candidates)
    )


class TissueConfig:
    """Singleton que carga y provee configuracion de tejidos."""

    _instance: Optional["TissueConfig"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        path = _find_config_path()
        with open(path, "r", encoding="utf-8") as f:
            self._raw = json.load(f)

        self._by_index: dict[int, dict] = {}
        for t in self._raw.get("tissues", []):
            self._by_index[t["index"]] = t

        # TS mapping: keys como strings en JSON, convertir a int
        ts_raw = self._raw.get("ts_label_to_phantom", {})
        self._ts_mapping: dict[int, int] = {int(k): v for k, v in ts_raw.items()}

        self._body_labels: set[int] = set(self._raw.get("ts_body_labels", []))

        self._loaded = True
        logger.info(f"TissueConfig cargado: {len(self._by_index)} tejidos")

    # ------------------------------------------------------------------
    # ACCESO A TEJIDOS
    # ------------------------------------------------------------------

    def get_tissue(self, index: int) -> Optional[dict]:
        """Retorna dict del tejido por su indice 3Dosim, o None."""
        return self._by_index.get(index)

    def get_all_tissues(self) -> list[dict]:
        """Retorna lista de todos los tejidos."""
        return list(self._raw.get("tissues", []))

    def get_tissue_indices(self) -> list[int]:
        """Retorna indices disponibles."""
        return sorted(self._by_index.keys())

    def get_tissue_name(self, index: int) -> str:
        """Nombre en español del tejido."""
        t = self.get_tissue(index)
        return t["name"] if t else f"Desconocido_{index}"

    def get_tissue_color(self, index: int) -> tuple[float, float, float]:
        """Color RGB del tejido."""
        t = self.get_tissue(index)
        if t:
            c = t["color"]
            return (float(c[0]), float(c[1]), float(c[2]))
        return (0.5, 0.5, 0.5)

    def get_tissue_density(self, index: int) -> float:
        """Densidad en g/cm3."""
        t = self.get_tissue(index)
        return float(t["density_gcm3"]) if t else 1.0

    def get_tissue_hu_range(self, index: int) -> tuple[int, int]:
        """Rango de HU."""
        t = self.get_tissue(index)
        if t:
            r = t["hu_range"]
            return (int(r[0]), int(r[1]))
        return (-1024, 2000)

    def get_stats_key(self, name: str) -> str:
        """Convierte nombre de tejido a key para estadisticas.
        Ej: 'Higado' -> 'liver_vol_ml', 'Tejido_blando' -> 'soft_tissue_vol_ml'
        """
        name_map = {
            "Aire": "air_vol_ml",
            "Tejido_blando": "soft_tissue_vol_ml",
            "Pulmon": "lung_vol_ml",
            "Hueso": "bone_vol_ml",
            "Higado": "liver_vol_ml",
            "Tumor": "tumor_vol_ml",
        }
        return name_map.get(name, f"{name.lower()}_vol_ml")

    # ------------------------------------------------------------------
    # MATERIALES MCNP
    # ------------------------------------------------------------------

    def get_mcnp_material(self, index: int) -> Optional[dict]:
        """Retorna config de material MCNP para el tejido, o None."""
        t = self.get_tissue(index)
        return t["mcnp_material"] if t else None

    def get_mcnp_material_id(self, index: int) -> int:
        """ID numerico del material MCNP."""
        mat = self.get_mcnp_material(index)
        return int(mat["id"]) if mat else 0

    def get_mcnp_composition(self, index: int) -> dict[str, float]:
        """Composicion elemental: {ZAID: mass_fraction}."""
        mat = self.get_mcnp_material(index)
        return dict(mat["composition"]) if mat else {}

    def generate_mcnp_material_card(self, index: int) -> str:
        """
        Genera tarjeta MCNP para el material del tejido.
        Formato: M<id>  <zaid1> <frac1>  <zaid2> <frac2> ...
        """
        mat = self.get_mcnp_material(index)
        if not mat:
            return ""
        tid = mat["id"]
        comp = mat["composition"]
        parts = [f"M{tid}"]
        for zaid, frac in comp.items():
            parts.append(f"  {zaid}  {frac}")
        return "".join(parts)

    def generate_all_material_cards(self, indices: list[int]) -> list[str]:
        """Genera tarjetas M para todos los indices dados."""
        cards = []
        for idx in sorted(set(indices)):
            card = self.generate_mcnp_material_card(idx)
            if card:
                cards.append(card)
        return cards

    # ------------------------------------------------------------------
    # MAPPING TS -> PHANTOM
    # ------------------------------------------------------------------

    def get_ts_mapping(self) -> dict[int, int]:
        """Mapping: label de TotalSegmentator -> indice phantom."""
        return dict(self._ts_mapping)

    def get_body_labels(self) -> set[int]:
        """Labels TS que definen el cuerpo (tejido blando)."""
        return set(self._body_labels)

    def map_ts_to_phantom_label(self, ts_label: int) -> int:
        """Convierte un label de TS a indice phantom.
        Si no esta en el mapping explicito, verifica si es body_label -> 30,
        caso contrario -> 1 (aire).
        """
        if ts_label in self._ts_mapping:
            return self._ts_mapping[ts_label]
        if ts_label in self._body_labels:
            return 30
        return 1

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Retorna el JSON completo como dict."""
        return dict(self._raw)
