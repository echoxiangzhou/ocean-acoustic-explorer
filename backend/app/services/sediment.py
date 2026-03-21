"""
Deck41 seafloor sediment service.

Data format (verified):
  - File: DECK41_NEW.csv (36,401 records)
  - Columns: OBJECTID, LATITUDE, LONGITUDE, LITH1, LITH2, DESC_, WDEPTH, DEVICE, ...
  - LITH1/LITH2: text descriptions (sand, silt, clay, gravel, etc.)
  - WDEPTH: water depth in meters (integer)

Used for Module C acoustic modeling: bottom boundary conditions.
Maps sediment types to acoustic properties (density, sound speed, attenuation).
"""

import csv
import numpy as np
from functools import lru_cache
from scipy.spatial import cKDTree
from app.config import DATA_DIR

DECK41_PATH = f"{DATA_DIR}/deck41/DECK41_NEW.csv"

# Sediment type -> acoustic properties mapping
# Based on Hamilton (1980) and APL-UW TR 9407
SEDIMENT_ACOUSTICS = {
    "gravel": {"density": 2.0, "speed": 1800, "attenuation": 0.6, "code": 1},
    "sand": {"density": 1.9, "speed": 1650, "attenuation": 0.8, "code": 2},
    "silt": {"density": 1.7, "speed": 1550, "attenuation": 1.0, "code": 3},
    "clay": {"density": 1.5, "speed": 1500, "attenuation": 0.2, "code": 4},
    "mud": {"density": 1.5, "speed": 1480, "attenuation": 0.2, "code": 5},
    "rock": {"density": 2.5, "speed": 2500, "attenuation": 0.1, "code": 6},
    "chalk": {"density": 2.2, "speed": 2400, "attenuation": 0.2, "code": 7},
    "limestone": {"density": 2.4, "speed": 3000, "attenuation": 0.1, "code": 8},
    "coral": {"density": 1.8, "speed": 1700, "attenuation": 0.5, "code": 9},
    "ooze": {"density": 1.4, "speed": 1470, "attenuation": 0.1, "code": 10},
}

# Default for unknown/unmatched types
DEFAULT_ACOUSTIC = {"density": 1.6, "speed": 1550, "attenuation": 0.5, "code": 0}


@lru_cache(maxsize=1)
def _load_deck41():
    """Load deck41 CSV and build spatial index."""
    lats = []
    lons = []
    records = []

    with open(DECK41_PATH, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get("LATITUDE", ""))
                lon = float(row.get("LONGITUDE", ""))
            except (ValueError, TypeError):
                continue

            lats.append(lat)
            lons.append(lon)
            records.append({
                "lat": lat,
                "lon": lon,
                "lith1": row.get("LITH1", "").strip().lower(),
                "lith2": row.get("LITH2", "").strip().lower(),
                "desc": row.get("DESC_", "").strip(),
                "wdepth": _safe_float(row.get("WDEPTH", "")),
            })

    coords = np.column_stack([np.radians(lats), np.radians(lons)])
    tree = cKDTree(coords)

    return records, tree


def _safe_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _classify_sediment(lith1: str) -> dict:
    """Map LITH1 text to acoustic properties."""
    for key, props in SEDIMENT_ACOUSTICS.items():
        if key in lith1:
            return props
    return DEFAULT_ACOUSTIC


def query_sediment(lat: float, lon: float, max_distance_km: float = 100.0) -> dict:
    """
    Find nearest deck41 sediment sample and return acoustic properties.

    Args:
        lat, lon: query location
        max_distance_km: max search radius

    Returns:
        dict with sediment type, acoustic properties, and distance
    """
    records, tree = _load_deck41()

    query_point = np.array([np.radians(lat), np.radians(lon)])
    dist, idx = tree.query(query_point)

    # Convert radian distance to km (approximate)
    distance_km = dist * 6371.0

    if distance_km > max_distance_km:
        return {
            "found": False,
            "distance_km": distance_km,
            "sediment": "unknown",
            "acoustic": DEFAULT_ACOUSTIC,
        }

    record = records[idx]
    acoustic = _classify_sediment(record["lith1"])

    return {
        "found": True,
        "distance_km": round(distance_km, 1),
        "sample_lat": record["lat"],
        "sample_lon": record["lon"],
        "lith1": record["lith1"],
        "lith2": record["lith2"],
        "description": record["desc"],
        "water_depth": record["wdepth"],
        "acoustic": acoustic,
    }
