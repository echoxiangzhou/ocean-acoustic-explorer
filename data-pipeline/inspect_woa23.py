#!/usr/bin/env python3
import netCDF4 as nc
import sys

f = sys.argv[1] if len(sys.argv) > 1 else "/data/nas_data/ocean_acoustic/woa23/temperature/woa23_decav91C0_t01_04.nc"
ds = nc.Dataset(f)

print("--- Dimensions ---")
for d in ds.dimensions:
    print("  %s: %d" % (d, len(ds.dimensions[d])))

print("--- Variables ---")
for v in ds.variables:
    var = ds.variables[v]
    print("  %s: dims=%s shape=%s" % (v, str(var.dimensions), str(var.shape)))
    if hasattr(var, "units"):
        print("    units=%s" % var.units)
    if hasattr(var, "long_name"):
        print("    long_name=%s" % var.long_name)

print("--- Depth values ---")
depth = ds.variables["depth"][:]
print("  first 10:", depth[:10].tolist())
print("  last 5:", depth[-5:].tolist())
print("  total:", len(depth))

lat = ds.variables["lat"][:]
print("--- Lat: %.2f to %.2f, step=%.4f, count=%d" % (lat[0], lat[-1], lat[1]-lat[0], len(lat)))

lon = ds.variables["lon"][:]
print("--- Lon: %.2f to %.2f, step=%.4f, count=%d" % (lon[0], lon[-1], lon[1]-lon[0], len(lon)))

ds.close()
