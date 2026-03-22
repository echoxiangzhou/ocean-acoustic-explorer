"""
Section sound speed field computation for Module C.

Given two endpoints on the map, constructs a 2D sound speed field c(range, depth)
along the section by interpolating WOA23 T/S profiles at regular intervals.

Also provides the bathymetry profile from GEBCO along the section.
"""

import numpy as np
import gsw
from app.services.zarr_reader import load_woa23_month
from app.services.bathymetry import get_section_bathymetry


def compute_section_field(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    month: int = 1,
    num_range_points: int = 200,
    formula: str = "teos10",
) -> dict:
    """
    Compute 2D sound speed field along a section.

    Returns:
        dict with:
          - range_km: array of distances (km)
          - depth: array of depth levels (m)
          - sound_speed: 2D array c(range, depth)
          - temperature: 2D array T(range, depth)
          - salinity: 2D array S(range, depth)
          - bathymetry: bottom depth along section (m)
          - lat/lon: coordinates of section points
    """
    ds_t, ds_s = load_woa23_month(month)

    # Support both lat/lon (NetCDF) and latitude/longitude (Zarr) naming
    lat_name = "latitude" if "latitude" in ds_t.dims else "lat"
    lon_name = "longitude" if "longitude" in ds_t.dims else "lon"
    lat_arr = ds_t[lat_name].values
    lon_arr = ds_t[lon_name].values
    depth = ds_t.depth.values  # 57 levels

    # Generate points along section
    lats = np.linspace(start_lat, end_lat, num_range_points)
    lons = np.linspace(start_lon, end_lon, num_range_points)

    # Compute distances
    bathy = get_section_bathymetry(start_lat, start_lon, end_lat, end_lon, num_range_points)
    range_km = np.array(bathy["distance_km"])
    bottom_depth = np.array(bathy["depth"])

    # Build 2D T/S fields by nearest-neighbor lookup
    temp_2d = np.full((num_range_points, len(depth)), np.nan, dtype=np.float32)
    salt_2d = np.full((num_range_points, len(depth)), np.nan, dtype=np.float32)
    ss_2d = np.full((num_range_points, len(depth)), np.nan, dtype=np.float32)

    # Get full 3D arrays (already in memory from cache)
    t_an = ds_t["t_an"]
    s_an = ds_s["s_an"]
    if "time" in t_an.dims:
        t_all = t_an.values[0]  # (57, 720, 1440)
        s_all = s_an.values[0]
    else:
        t_all = t_an.values
        s_all = s_an.values

    for i, (lat, lon) in enumerate(zip(lats, lons)):
        lat_idx = int(np.abs(lat_arr - lat).argmin())
        lon_idx = int(np.abs(lon_arr - lon).argmin())

        t_prof = t_all[:, lat_idx, lon_idx]
        s_prof = s_all[:, lat_idx, lon_idx]

        valid = ~np.isnan(t_prof) & ~np.isnan(s_prof)
        if valid.sum() < 3:
            continue

        temp_2d[i, :] = t_prof
        salt_2d[i, :] = s_prof

        # Compute sound speed for valid points
        d = depth[valid]
        t = t_prof[valid]
        s = s_prof[valid]

        pressure = gsw.p_from_z(-d, lat)
        sa = gsw.SA_from_SP(s, pressure, lon, lat)
        ct = gsw.CT_from_t(sa, t, pressure)
        ss = gsw.sound_speed(sa, ct, pressure)

        ss_2d[i, valid] = ss

        # Mask below ocean bottom
        for j in range(len(depth)):
            if depth[j] > bottom_depth[i]:
                ss_2d[i, j] = np.nan
                temp_2d[i, j] = np.nan
                salt_2d[i, j] = np.nan

    return {
        "range_km": range_km.tolist(),
        "depth": depth.tolist(),
        "sound_speed": ss_2d.tolist(),
        "temperature": temp_2d.tolist(),
        "salinity": salt_2d.tolist(),
        "bathymetry": bottom_depth.tolist(),
        "lat": lats.tolist(),
        "lon": lons.tolist(),
        "section_length_km": float(range_km[-1]),
    }
