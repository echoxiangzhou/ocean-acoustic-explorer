"""
GEBCO 2024 bathymetry service.

GEBCO data structure (verified):
  - File: GEBCO_2024.nc
  - Variable: elevation (int16), dims=(lat=43200, lon=86400)
  - Resolution: 15 arc-second (~0.004167°)
  - Values: negative = ocean depth (m), positive = land elevation (m)
  - Coordinates: lat (-89.998 ~ 89.998), lon (-179.998 ~ 179.998)
"""

import numpy as np
import xarray as xr
from functools import lru_cache
from app.config import GEBCO_PATH


@lru_cache(maxsize=1)
def _load_gebco():
    """Load GEBCO dataset. Lazy loaded, cached."""
    return xr.open_dataset(GEBCO_PATH)


def get_depth(lat: float, lon: float) -> float:
    """
    Get ocean depth at a point (positive value in meters).
    Returns 0 for land points.
    """
    ds = _load_gebco()
    lat_idx = int(np.abs(ds.lat.values - lat).argmin())
    lon_idx = int(np.abs(ds.lon.values - lon).argmin())
    elevation = float(ds["elevation"].values[lat_idx, lon_idx])
    return max(0.0, -elevation)  # Convert to positive depth


def get_section_bathymetry(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    num_points: int = 500,
) -> dict:
    """
    Extract bathymetry profile along a section (two endpoints).
    Returns distances (km) and depths (m, positive downward).
    """
    ds = _load_gebco()

    # Interpolate points along great circle (simplified: linear for short sections)
    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)

    depths = []
    for lat, lon in zip(lats, lons):
        lat_idx = int(np.abs(ds.lat.values - lat).argmin())
        lon_idx = int(np.abs(ds.lon.values - lon).argmin())
        elev = float(ds["elevation"].values[lat_idx, lon_idx])
        depths.append(max(0.0, -elev))

    # Compute distances along section (Haversine)
    distances = _compute_distances(lats, lons)

    return {
        "lat": lats.tolist(),
        "lon": lons.tolist(),
        "distance_km": distances,
        "depth": depths,
    }


def _compute_distances(lats: np.ndarray, lons: np.ndarray) -> list:
    """Compute cumulative distances in km along a series of lat/lon points."""
    R = 6371.0  # Earth radius in km
    distances = [0.0]
    for i in range(1, len(lats)):
        lat1, lon1 = np.radians(lats[i - 1]), np.radians(lons[i - 1])
        lat2, lon2 = np.radians(lats[i]), np.radians(lons[i])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distances.append(distances[-1] + R * c)
    return distances
