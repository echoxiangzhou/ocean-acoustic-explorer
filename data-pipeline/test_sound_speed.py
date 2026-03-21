#!/usr/bin/env python3
"""Test sound speed computation with real WOA23 data."""

import sys
import os
import numpy as np

# Simulate app.config
class Config:
    WOA23_DIR = "/data/nas_data/ocean_acoustic/woa23"

sys.modules['app'] = type(sys)('app')
sys.modules['app.config'] = Config

import xarray as xr
import gsw

WOA23_DIR = Config.WOA23_DIR

def test_profile(lat, lon, month):
    month_str = str(month).zfill(2)
    t_path = "%s/temperature/woa23_decav91C0_t%s_04.nc" % (WOA23_DIR, month_str)
    s_path = "%s/salinity/woa23_decav91C0_s%s_04.nc" % (WOA23_DIR, month_str)

    print("Loading T: %s" % t_path)
    print("Loading S: %s" % s_path)

    ds_t = xr.open_dataset(t_path, decode_times=False)
    ds_s = xr.open_dataset(s_path, decode_times=False)

    # Find nearest grid point
    lat_idx = int(np.abs(ds_t.lat.values - lat).argmin())
    lon_idx = int(np.abs(ds_t.lon.values - lon).argmin())
    actual_lat = float(ds_t.lat.values[lat_idx])
    actual_lon = float(ds_t.lon.values[lon_idx])
    print("Requested: (%.2f, %.2f) -> Nearest grid: (%.2f, %.2f)" % (lat, lon, actual_lat, actual_lon))

    # Extract profiles
    temp = ds_t["t_an"].values[0, :, lat_idx, lon_idx]
    salt = ds_s["s_an"].values[0, :, lat_idx, lon_idx]
    depth = ds_t["depth"].values

    valid = ~np.isnan(temp) & ~np.isnan(salt)
    d = depth[valid]
    t = temp[valid]
    s = salt[valid]
    print("Valid depth levels: %d / %d" % (len(d), len(depth)))
    print("Depth range: %.0f - %.0f m" % (d[0], d[-1]))
    print("Temp range: %.2f - %.2f C" % (np.min(t), np.max(t)))
    print("Salt range: %.2f - %.2f PSU" % (np.min(s), np.max(s)))

    # TEOS-10 sound speed
    pressure = gsw.p_from_z(-d, actual_lat)
    sa = gsw.SA_from_SP(s, pressure, actual_lon, actual_lat)
    ct = gsw.CT_from_t(sa, t, pressure)
    ss = gsw.sound_speed(sa, ct, pressure)

    print("\n--- Sound Speed Profile (TEOS-10) ---")
    for i in range(0, len(d), max(1, len(d)//15)):
        print("  %6.0fm: T=%.2fC  S=%.2f  c=%.2f m/s" % (d[i], t[i], s[i], ss[i]))

    # Features
    min_idx = int(np.argmin(ss))
    print("\n--- Features ---")
    print("  Surface speed:     %.2f m/s" % ss[0])
    print("  Channel axis:      %.0f m (%.2f m/s)" % (d[min_idx], ss[min_idx]))
    print("  Delta c:           %.2f m/s" % (ss[0] - ss[min_idx]))

    # Surface duct
    duct = 0
    for i in range(1, len(ss)):
        if ss[i] < ss[i-1]:
            duct = d[i-1]
            break
    print("  Surface duct:      %.0f m" % duct)

    ds_t.close()
    ds_s.close()

# Test key ocean locations
print("=" * 60)
print("TEST 1: South China Sea (18N, 115E) - January")
print("=" * 60)
test_profile(18.0, 115.0, 1)

print("\n" + "=" * 60)
print("TEST 2: South China Sea (18N, 115E) - July")
print("=" * 60)
test_profile(18.0, 115.0, 7)

print("\n" + "=" * 60)
print("TEST 3: Northwest Pacific (30N, 140E) - January")
print("=" * 60)
test_profile(30.0, 140.0, 1)

print("\n" + "=" * 60)
print("TEST 4: North Atlantic (40N, 30W) - January")
print("=" * 60)
test_profile(40.0, -30.0, 1)
