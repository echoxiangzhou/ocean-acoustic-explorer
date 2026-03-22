"""
xpublish-wms server for OceanAcoustic Explorer.

Preloads all feature data into memory at startup for fast tile serving.
Total memory: ~30MB features + ~2MB SST = ~32MB.
"""

import os
import glob
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

ZARR_DIR = os.getenv("ZARR_DIR", "/data/zarr")
FEATURES_DIR = os.getenv("FEATURES_DIR", "/data/features")
WOA23_DIR = os.getenv("WOA23_DIR", "/data/woa23")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))


def _make_cf(ds: xr.Dataset) -> xr.Dataset:
    """Ensure CF-compliant coordinate names."""
    if "lat" in ds.dims:
        ds = ds.rename({"lat": "latitude", "lon": "longitude"})
    if "latitude" in ds.coords:
        ds["latitude"].attrs.update({"units": "degrees_north", "standard_name": "latitude", "axis": "Y"})
        ds["longitude"].attrs.update({"units": "degrees_east", "standard_name": "longitude", "axis": "X"})
    return ds


def load_datasets() -> dict:
    datasets = {}

    # 1. Load features from Zarr (preferred, chunked)
    features_zarr = os.path.join(ZARR_DIR, "features.zarr")
    if os.path.isdir(features_zarr):
        print("Loading features from Zarr...")
        ds_features = xr.open_zarr(features_zarr)
        # Preload into memory for maximum speed
        ds_features.load()
        print("  Features loaded into memory: %.1fMB" % (
            sum(ds_features[v].nbytes for v in ds_features.data_vars) / 1e6))

        for month in range(1, 13):
            ds_m = ds_features.sel(month=month, drop=True)
            for var in ds_m.data_vars:
                datasets["%s_m%02d" % (var, month)] = ds_m[[var]]
                if month == 1:
                    datasets[var] = ds_m[[var]]

    # 2. Fallback: load from NetCDF
    elif os.path.isdir(FEATURES_DIR):
        print("Loading features from NetCDF...")
        files = sorted(glob.glob(os.path.join(FEATURES_DIR, "features_month*_src50m.nc")))
        for fpath in files:
            month_str = os.path.basename(fpath).replace("features_month", "").replace("_src50m.nc", "")
            ds = xr.open_dataset(fpath)
            ds = _make_cf(ds)
            ds.load()  # Into memory
            for var in ds.data_vars:
                datasets["%s_m%s" % (var, month_str)] = ds[[var]]
                if month_str == "01":
                    datasets[var] = ds[[var]]
        print("  Loaded %d feature files" % len(files))

    # 3. WOA23 SST (surface temp, month 01) - small
    t_path = os.path.join(WOA23_DIR, "temperature", "woa23_decav91C0_t01_04.nc")
    if os.path.exists(t_path):
        ds_t = xr.open_dataset(t_path, decode_times=False)
        ds_sst = ds_t[["t_an"]].isel(depth=0, time=0, drop=True)
        ds_sst = ds_sst.rename({"t_an": "sea_surface_temperature"})
        ds_sst = _make_cf(ds_sst)
        ds_sst.load()
        datasets["sst"] = ds_sst
        print("  Loaded SST")

    return datasets


def create_app():
    datasets = load_datasets()
    if not datasets:
        print("WARNING: No datasets loaded.")
        datasets["empty"] = xr.Dataset()

    print("Serving %d WMS datasets, all preloaded in memory" % len(datasets))
    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
