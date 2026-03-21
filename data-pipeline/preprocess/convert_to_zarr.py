#!/usr/bin/env python3
"""
Convert all NetCDF data to Zarr format for faster random access.

Zarr advantages over NetCDF for WMS tile serving:
  - Chunked storage enables parallel/random reads
  - No file-level locks, supports concurrent access
  - Cloud-native, works with fsspec/S3

Converts:
  1. Precomputed features (12 months x 6 vars) -> single features.zarr
  2. WOA23 T/S (12 months x 57 depths) -> woa23_temperature.zarr, woa23_salinity.zarr
  3. GEBCO bathymetry -> gebco.zarr (coarsened to 0.05° for WMS, original kept)

Usage:
    python3 convert_to_zarr.py                # Convert all
    python3 convert_to_zarr.py features       # Features only
    python3 convert_to_zarr.py woa23          # WOA23 only
    python3 convert_to_zarr.py gebco          # GEBCO only
"""

import sys
import os
import glob
import numpy as np
import xarray as xr
from datetime import datetime

DATA_DIR = "/data/nas_data/ocean_acoustic"
ZARR_DIR = "/data/nas_data/ocean_acoustic/zarr"


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def convert_features():
    """Convert precomputed feature NetCDF files to single Zarr store."""
    features_dir = os.path.join(DATA_DIR, "features")
    out_path = os.path.join(ZARR_DIR, "features.zarr")

    files = sorted(glob.glob(os.path.join(features_dir, "features_month*_src50m.nc")))
    if not files:
        log("No feature files found")
        return

    log("Converting %d feature files to Zarr..." % len(files))

    ds_list = []
    for f in files:
        ds = xr.open_dataset(f)
        ds_list.append(ds)

    # Concat along month dimension
    ds_all = xr.concat(ds_list, dim="month")
    ds_all["month"] = list(range(1, len(ds_list) + 1))

    # Rename for CF compliance (xpublish-wms requirement)
    ds_all = ds_all.rename({"lat": "latitude", "lon": "longitude"})
    ds_all["latitude"].attrs.update({
        "units": "degrees_north", "standard_name": "latitude", "axis": "Y",
    })
    ds_all["longitude"].attrs.update({
        "units": "degrees_east", "standard_name": "longitude", "axis": "X",
    })

    # Optimal chunks for WMS tile access (256x256 tiles at 0.25°)
    chunks = {"month": 1, "latitude": 180, "longitude": 360}
    ds_all = ds_all.chunk(chunks)

    # Write Zarr
    if os.path.exists(out_path):
        import shutil
        shutil.rmtree(out_path)

    ds_all.to_zarr(out_path, mode="w")

    size_mb = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, dn, filenames in os.walk(out_path)
        for f in filenames
    ) / 1e6
    log("Features Zarr saved: %s (%.1fMB)" % (out_path, size_mb))
    log("  Vars: %s" % list(ds_all.data_vars))
    log("  Dims: %s" % dict(ds_all.dims))
    log("  Chunks: %s" % str(chunks))

    for ds in ds_list:
        ds.close()


def convert_woa23():
    """Convert WOA23 T/S NetCDF files to Zarr stores."""
    woa_dir = os.path.join(DATA_DIR, "woa23")

    for var_name, subdir, nc_var in [
        ("temperature", "temperature", "t_an"),
        ("salinity", "salinity", "s_an"),
    ]:
        out_path = os.path.join(ZARR_DIR, "woa23_%s.zarr" % var_name)

        files = sorted(glob.glob(
            os.path.join(woa_dir, subdir, "woa23_decav91C0_%s*_04.nc" % nc_var[0])
        ))
        # Filter to months 01-12 only (exclude 00=annual)
        files = [f for f in files if not f.endswith("00_04.nc")]

        if not files:
            log("No WOA23 %s files found" % var_name)
            continue

        log("Converting %d WOA23 %s files to Zarr..." % (len(files), var_name))

        ds_list = []
        for f in files:
            ds = xr.open_dataset(f, decode_times=False)
            # Keep only the analyzed field
            ds = ds[[nc_var]].isel(time=0, drop=True)
            ds_list.append(ds)

        ds_all = xr.concat(ds_list, dim="month")
        ds_all["month"] = list(range(1, len(ds_list) + 1))

        # CF compliance
        ds_all = ds_all.rename({"lat": "latitude", "lon": "longitude"})
        ds_all["latitude"].attrs.update({
            "units": "degrees_north", "standard_name": "latitude", "axis": "Y",
        })
        ds_all["longitude"].attrs.update({
            "units": "degrees_east", "standard_name": "longitude", "axis": "X",
        })

        # Chunks: 1 month, all depths, spatial tiles
        chunks = {"month": 1, "depth": 57, "latitude": 180, "longitude": 360}
        ds_all = ds_all.chunk(chunks)

        if os.path.exists(out_path):
            import shutil
            shutil.rmtree(out_path)

        ds_all.to_zarr(out_path, mode="w")

        size_mb = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, dn, filenames in os.walk(out_path)
            for f in filenames
        ) / 1e6
        log("WOA23 %s Zarr saved: %s (%.1fMB)" % (var_name, out_path, size_mb))

        for ds in ds_list:
            ds.close()


def convert_gebco():
    """Convert GEBCO to coarsened Zarr for WMS (original is too large for tile serving)."""
    gebco_path = os.path.join(DATA_DIR, "gebco", "GEBCO_2024.nc")
    out_path = os.path.join(ZARR_DIR, "gebco_coarse.zarr")

    if not os.path.exists(gebco_path):
        log("GEBCO file not found")
        return

    log("Loading GEBCO and coarsening for WMS...")
    ds = xr.open_dataset(gebco_path)

    # Coarsen from 15 arc-sec (~43200x86400) to ~0.05° (~3600x7200)
    # Factor = 12 (15 arc-sec * 12 = 3 arc-min = 0.05°)
    ds_coarse = ds.coarsen(lat=12, lon=12, boundary="trim").mean()

    # CF compliance
    ds_coarse = ds_coarse.rename({"lat": "latitude", "lon": "longitude"})
    ds_coarse["latitude"].attrs.update({
        "units": "degrees_north", "standard_name": "latitude", "axis": "Y",
    })
    ds_coarse["longitude"].attrs.update({
        "units": "degrees_east", "standard_name": "longitude", "axis": "X",
    })

    chunks = {"latitude": 360, "longitude": 720}
    ds_coarse = ds_coarse.chunk(chunks)

    if os.path.exists(out_path):
        import shutil
        shutil.rmtree(out_path)

    ds_coarse.to_zarr(out_path, mode="w")

    size_mb = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, dn, filenames in os.walk(out_path)
        for f in filenames
    ) / 1e6
    log("GEBCO coarsened Zarr saved: %s (%.1fMB)" % (out_path, size_mb))

    ds.close()


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(ZARR_DIR, exist_ok=True)

    log("=== Convert to Zarr ===")

    if target in ("all", "features"):
        convert_features()
    if target in ("all", "woa23"):
        convert_woa23()
    if target in ("all", "gebco"):
        convert_gebco()

    log("=== Done ===")
    # List output
    for name in sorted(os.listdir(ZARR_DIR)):
        path = os.path.join(ZARR_DIR, name)
        if os.path.isdir(path):
            size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, fns in os.walk(path)
                for f in fns
            ) / 1e6
            log("  %s: %.1fMB" % (name, size))


if __name__ == "__main__":
    main()
