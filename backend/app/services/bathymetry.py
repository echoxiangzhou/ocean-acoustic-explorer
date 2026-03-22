"""
GEBCO 2024 bathymetry service (optimized).

GEBCO data: elevation (int16), (lat=43200, lon=86400), 15 arc-second.
Negative = ocean depth, positive = land.
"""

import numpy as np
import xarray as xr
from functools import lru_cache
from app.config import GEBCO_PATH


@lru_cache(maxsize=1)
def _load_gebco():
    """Load GEBCO dataset with precomputed coordinate arrays."""
    ds = xr.open_dataset(GEBCO_PATH)
    # Cache coordinate arrays for fast index lookup
    lat_arr = ds.lat.values
    lon_arr = ds.lon.values
    # Precompute step size for O(1) index calculation
    lat_step = (lat_arr[-1] - lat_arr[0]) / (len(lat_arr) - 1)
    lon_step = (lon_arr[-1] - lon_arr[0]) / (len(lon_arr) - 1)
    return ds, lat_arr, lon_arr, lat_step, lon_step


def _fast_index(val, arr_min, step, arr_len):
    """O(1) index lookup for uniform grid."""
    idx = int(round((val - arr_min) / step))
    return max(0, min(idx, arr_len - 1))


def get_depth(lat: float, lon: float) -> float:
    """Get ocean depth at a point (positive meters). 0 for land."""
    ds, lat_arr, lon_arr, lat_step, lon_step = _load_gebco()
    lat_idx = _fast_index(lat, lat_arr[0], lat_step, len(lat_arr))
    lon_idx = _fast_index(lon, lon_arr[0], lon_step, len(lon_arr))
    elevation = int(ds["elevation"].values[lat_idx, lon_idx])
    return max(0.0, float(-elevation))


def get_section_bathymetry(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    num_points: int = 500,
) -> dict:
    """Extract bathymetry profile along a section. Vectorized for speed."""
    ds, lat_arr, lon_arr, lat_step, lon_step = _load_gebco()

    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)

    # Vectorized O(1) index calculation
    lat_indices = np.clip(
        np.round((lats - lat_arr[0]) / lat_step).astype(int),
        0, len(lat_arr) - 1
    )
    lon_indices = np.clip(
        np.round((lons - lon_arr[0]) / lon_step).astype(int),
        0, len(lon_arr) - 1
    )

    # Vectorized lookup (coarsened GEBCO is small enough to fit in memory)
    elevations = ds["elevation"].values[lat_indices, lon_indices].astype(float)
    depths = np.maximum(0.0, -elevations)

    distances = _compute_distances(lats, lons)

    return {
        "lat": lats.tolist(),
        "lon": lons.tolist(),
        "distance_km": distances,
        "depth": depths.tolist(),
    }


def _compute_distances(lats: np.ndarray, lons: np.ndarray) -> list:
    """Cumulative Haversine distances in km."""
    R = 6371.0
    lat_r = np.radians(lats)
    lon_r = np.radians(lons)
    dlat = np.diff(lat_r)
    dlon = np.diff(lon_r)
    a = np.sin(dlat / 2)**2 + np.cos(lat_r[:-1]) * np.cos(lat_r[1:]) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    segs = R * c
    dists = np.concatenate([[0], np.cumsum(segs)])
    return dists.tolist()
