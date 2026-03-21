#!/usr/bin/env python3
"""Inspect GEBCO 2024 bathymetry data."""
import xarray as xr
import numpy as np

path = "/data/nas_data/ocean_acoustic/gebco/GEBCO_2024.nc"
print("Loading GEBCO: %s" % path)
ds = xr.open_dataset(path)

print("--- Dimensions ---")
for d in ds.dims:
    print("  %s: %d" % (d, ds.dims[d]))

print("--- Variables ---")
for v in ds.data_vars:
    var = ds[v]
    print("  %s: dims=%s shape=%s dtype=%s" % (v, str(var.dims), str(var.shape), var.dtype))
    if hasattr(var, "units"):
        print("    units=%s" % var.attrs.get("units", "N/A"))
    if hasattr(var, "long_name"):
        print("    long_name=%s" % var.attrs.get("long_name", "N/A"))

print("--- Coordinates ---")
for c in ds.coords:
    vals = ds[c].values
    print("  %s: %s to %s, count=%d" % (c, vals[0], vals[-1], len(vals)))

# Sample data at South China Sea
print("\n--- Sample: South China Sea (18N, 115E) ---")
elev = ds["elevation"]
lat_idx = int(np.abs(ds.lat.values - 18.0).argmin())
lon_idx = int(np.abs(ds.lon.values - 115.0).argmin())
val = float(elev.values[lat_idx, lon_idx])
print("  Elevation at (%.4f, %.4f): %.1f m" % (ds.lat.values[lat_idx], ds.lon.values[lon_idx], val))
print("  (negative = ocean depth)")

# Sample along 18N
print("\n--- Bathymetry profile along 18N, 110-120E ---")
lat_idx = int(np.abs(ds.lat.values - 18.0).argmin())
for lon_target in [110, 112, 114, 116, 118, 120]:
    lon_idx = int(np.abs(ds.lon.values - lon_target).argmin())
    val = float(elev.values[lat_idx, lon_idx])
    print("  18N, %dE: %.0f m" % (lon_target, val))

ds.close()
