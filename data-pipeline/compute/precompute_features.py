#!/usr/bin/env python3
"""
Precompute acoustic features from WOA23 data for Module A global overview.

Generates 6 feature layers as NetCDF files:
  1. channel_axis_depth (m)       - Sound channel axis depth
  2. surface_duct (m)             - Surface duct thickness
  3. thermocline_gradient (s^-1)  - Maximum thermocline gradient
  4. convergence_zone_km (km)     - First CZ distance (needs src_depth)
  5. shadow_zone_km (km)          - Shadow zone onset distance
  6. field_type (category)        - Sound field classification

Input: WOA23 T/S NetCDF (verified: t_an/s_an, 0.25°, 57 levels, 12 months)
       GEBCO bathymetry (verified: elevation int16, 15 arc-sec)
Output: NetCDF files in /data/nas_data/ocean_acoustic/features/

Usage:
    python3 precompute_features.py                  # All 12 months
    python3 precompute_features.py 1 3              # Jan-Mar only
    python3 precompute_features.py 1 1 --src-depth 100  # Jan, src=100m
"""

import sys
import os
import numpy as np
import xarray as xr
import gsw
from datetime import datetime

WOA23_DIR = "/data/nas_data/ocean_acoustic/woa23"
GEBCO_PATH = "/data/nas_data/ocean_acoustic/gebco/GEBCO_2024.nc"
OUTPUT_DIR = "/data/nas_data/ocean_acoustic/features"

SRC_DEPTHS = [50]  # Default source depths to precompute


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def load_gebco_coarsened(target_lat, target_lon):
    """Load GEBCO and resample to WOA23 0.25° grid."""
    log("Loading GEBCO bathymetry...")
    ds = xr.open_dataset(GEBCO_PATH)
    elev = ds["elevation"]

    # Coarsen GEBCO (15 arc-sec) to WOA23 (0.25° = 60 arc-sec, factor ~60)
    # Use nearest-neighbor lookup instead of coarsening (faster)
    depth_grid = np.full((len(target_lat), len(target_lon)), np.nan, dtype=np.float32)

    gebco_lat = ds.lat.values
    gebco_lon = ds.lon.values

    for i, lat in enumerate(target_lat):
        lat_idx = int(np.abs(gebco_lat - lat).argmin())
        for j, lon in enumerate(target_lon):
            lon_idx = int(np.abs(gebco_lon - lon).argmin())
            e = float(elev.values[lat_idx, lon_idx])
            depth_grid[i, j] = max(0.0, -e)

        if i % 100 == 0:
            log("  GEBCO resampling: %d/%d lat rows" % (i, len(target_lat)))

    ds.close()
    return depth_grid


def compute_sound_speed_profile(temp, salt, depth, lat, lon):
    """Compute TEOS-10 sound speed from T/S profile."""
    valid = ~np.isnan(temp) & ~np.isnan(salt)
    if valid.sum() < 3:
        return np.full_like(temp, np.nan)

    d = depth[valid]
    t = temp[valid]
    s = salt[valid]

    pressure = gsw.p_from_z(-d, lat)
    sa = gsw.SA_from_SP(s, pressure, lon, lat)
    ct = gsw.CT_from_t(sa, t, pressure)
    ss = gsw.sound_speed(sa, ct, pressure)

    result = np.full_like(temp, np.nan)
    result[valid] = ss
    return result


def extract_features(depth, ss, ocean_depth, lat, src_depth=50.0):
    """Extract features from one sound speed profile."""
    valid = ~np.isnan(ss)
    d = depth[valid]
    c = ss[valid]

    if len(c) < 3:
        return np.nan, 0.0, 0.0, np.nan, np.nan, 0

    # 1. Channel axis
    min_idx = int(np.argmin(c))
    axis_depth = float(d[min_idx])

    # 2. Surface duct
    duct = 0.0
    for i in range(1, len(c)):
        if c[i] < c[i - 1]:
            duct = float(d[i - 1])
            break

    # 3. Thermocline gradient
    dc = np.diff(c)
    dz = np.diff(d)
    dz[dz == 0] = 1.0
    grad = dc / dz
    neg = grad[grad < 0]
    thermo_grad = float(np.abs(np.min(neg))) if len(neg) > 0 else 0.0

    # 4. CZ distance (improved: extrapolate beyond 1500m)
    cz = np.nan
    if ocean_depth > 1000 and len(c) >= 5:
        src_idx = int(np.abs(d - src_depth).argmin())
        c_src = c[src_idx]
        c_min = float(np.min(c))
        delta_c = c_src - c_min

        if delta_c > 2.0:  # Need meaningful speed difference
            # Try to find critical depth in data
            below = c[min_idx:]
            d_below = d[min_idx:]
            crit_depth = np.nan
            for i in range(1, len(below)):
                if below[i] >= c_src:
                    frac = (c_src - below[i-1]) / (below[i] - below[i-1])
                    crit_depth = d_below[i-1] + frac * (d_below[i] - d_below[i-1])
                    break

            # If not found in data, extrapolate using deep-water gradient
            # Below 1000m, sound speed increases ~0.017 m/s per meter (pressure effect)
            if np.isnan(crit_depth) and len(c) >= 3:
                c_deep = c[-1]
                d_deep = d[-1]
                deep_gradient = 0.017  # m/s per meter (typical deep ocean)
                if c[-1] < c_src:
                    extra_depth = (c_src - c_deep) / deep_gradient
                    crit_depth = d_deep + extra_depth

            if not np.isnan(crit_depth) and crit_depth <= ocean_depth:
                H = crit_depth / 1000.0
                # CZ distance formula: R = 2 * sqrt(2 * R_earth * H * delta_c / c_min)
                cz_val = 2.0 * np.sqrt(2.0 * delta_c / c_min * 6371.0 * H)
                if 5 < cz_val < 300:
                    cz = cz_val

    # 5. Shadow zone (improved)
    sz = np.nan
    src_idx = int(np.abs(d - src_depth).argmin())
    if src_idx > 0 and src_idx < len(c) - 1:
        # Use centered difference for gradient
        dc_dz = (c[src_idx + 1] - c[src_idx - 1]) / (d[src_idx + 1] - d[src_idx - 1])
        if dc_dz < -0.001:  # Negative gradient (thermocline)
            # Shadow zone onset ~ skip distance of limiting ray
            c_src_val = c[src_idx]
            # R_shadow ≈ sqrt(2 * c * |dz| / |dc/dz|) for circular ray paths
            dz_to_axis = abs(d[min_idx] - src_depth)
            if dz_to_axis > 10:
                sz_val = np.sqrt(2.0 * c_src_val * dz_to_axis / abs(dc_dz)) / 1000.0
                if 1 < sz_val < 200:
                    sz = sz_val

    # 6. Field type
    if ocean_depth < 200:
        ftype = 2
    elif abs(lat) > 50 and axis_depth < 100:
        ftype = 3
    elif axis_depth > 500 and ocean_depth > 3000:
        ftype = 1
    else:
        ftype = 4

    return axis_depth, duct, thermo_grad, cz, sz, ftype


def process_month(month, depth_grid, src_depth=50.0):
    """Process one month of WOA23 data."""
    month_str = "%02d" % month
    t_path = "%s/temperature/woa23_decav91C0_t%s_04.nc" % (WOA23_DIR, month_str)
    s_path = "%s/salinity/woa23_decav91C0_s%s_04.nc" % (WOA23_DIR, month_str)

    log("Loading WOA23 month %d..." % month)
    ds_t = xr.open_dataset(t_path, decode_times=False)
    ds_s = xr.open_dataset(s_path, decode_times=False)

    lat = ds_t.lat.values      # (720,)
    lon = ds_t.lon.values      # (1440,)
    depth = ds_t.depth.values  # (57,)
    nlat, nlon = len(lat), len(lon)

    # Output arrays
    axis = np.full((nlat, nlon), np.nan, dtype=np.float32)
    duct = np.full((nlat, nlon), np.nan, dtype=np.float32)
    grad = np.full((nlat, nlon), np.nan, dtype=np.float32)
    cz = np.full((nlat, nlon), np.nan, dtype=np.float32)
    sz = np.full((nlat, nlon), np.nan, dtype=np.float32)
    ftype = np.zeros((nlat, nlon), dtype=np.int8)

    temp_all = ds_t["t_an"].values[0]  # (57, 720, 1440)
    salt_all = ds_s["s_an"].values[0]  # (57, 720, 1440)

    log("Computing features for month %d (720 x 1440 grid)..." % month)
    for i in range(nlat):
        for j in range(nlon):
            t_prof = temp_all[:, i, j]
            s_prof = salt_all[:, i, j]
            ocean_d = depth_grid[i, j]

            if np.all(np.isnan(t_prof)) or ocean_d <= 0:
                continue  # Land point

            ss = compute_sound_speed_profile(t_prof, s_prof, depth, lat[i], lon[j])
            a, d_val, g, c_val, s_val, f = extract_features(
                depth, ss, ocean_d, lat[i], src_depth
            )
            axis[i, j] = a
            duct[i, j] = d_val
            grad[i, j] = g
            cz[i, j] = c_val
            sz[i, j] = s_val
            ftype[i, j] = f

        if i % 50 == 0:
            log("  Row %d/%d (%.1f%%)" % (i, nlat, 100.0 * i / nlat))

    ds_t.close()
    ds_s.close()

    # Save as NetCDF
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    outfile = "%s/features_month%02d_src%dm.nc" % (OUTPUT_DIR, month, int(src_depth))

    ds_out = xr.Dataset(
        {
            "channel_axis_depth": (["lat", "lon"], axis, {"units": "m", "long_name": "Sound channel axis depth"}),
            "surface_duct": (["lat", "lon"], duct, {"units": "m", "long_name": "Surface duct thickness"}),
            "thermocline_gradient": (["lat", "lon"], grad, {"units": "1/s", "long_name": "Max thermocline sound speed gradient"}),
            "convergence_zone_km": (["lat", "lon"], cz, {"units": "km", "long_name": "First convergence zone distance"}),
            "shadow_zone_km": (["lat", "lon"], sz, {"units": "km", "long_name": "Shadow zone onset distance"}),
            "field_type": (["lat", "lon"], ftype, {"long_name": "Sound field type: 1=CZ, 2=shallow, 3=polar, 4=mixed"}),
        },
        coords={"lat": lat, "lon": lon},
        attrs={
            "source": "WOA23 + GEBCO 2024",
            "formula": "TEOS-10 (gsw)",
            "src_depth_m": src_depth,
            "month": month,
        },
    )
    ds_out.to_netcdf(outfile, encoding={
        v: {"zlib": True, "complevel": 4} for v in ds_out.data_vars
    })
    log("Saved: %s (%.1fMB)" % (outfile, os.path.getsize(outfile) / 1e6))


def main():
    args = sys.argv[1:]
    start_month = int(args[0]) if len(args) > 0 else 1
    end_month = int(args[1]) if len(args) > 1 else 12
    src_depth = 50.0
    for a in args:
        if a.startswith("--src-depth"):
            src_depth = float(args[args.index(a) + 1])

    log("=== Precompute Acoustic Features ===")
    log("Months: %d-%d, src_depth: %.0fm" % (start_month, end_month, src_depth))

    # Load GEBCO bathymetry at WOA23 resolution
    ds_t = xr.open_dataset(
        "%s/temperature/woa23_decav91C0_t01_04.nc" % WOA23_DIR,
        decode_times=False,
    )
    target_lat = ds_t.lat.values
    target_lon = ds_t.lon.values
    ds_t.close()

    depth_grid = load_gebco_coarsened(target_lat, target_lon)

    for month in range(start_month, end_month + 1):
        t0 = datetime.now()
        process_month(month, depth_grid, src_depth)
        elapsed = (datetime.now() - t0).total_seconds()
        log("Month %d done in %.0f seconds" % (month, elapsed))

    log("=== All done ===")


if __name__ == "__main__":
    main()
