"""
xpublish-wms server for OceanAcoustic Explorer.

Preloads all feature data into memory at startup.
NaN values replaced with _FillValue for correct transparent rendering.
"""

import os
import glob
import numpy as np
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

ZARR_DIR = os.getenv("ZARR_DIR", "/data/zarr")
FEATURES_DIR = os.getenv("FEATURES_DIR", "/data/features")
WOA23_DIR = os.getenv("WOA23_DIR", "/data/woa23")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))

FILL_VALUE = -9999.0


def _make_cf(ds: xr.Dataset) -> xr.Dataset:
    """Ensure CF-compliant coordinates and handle NaN."""
    if "lat" in ds.dims:
        ds = ds.rename({"lat": "latitude", "lon": "longitude"})
    if "latitude" in ds.coords:
        ds["latitude"].attrs.update({"units": "degrees_north", "standard_name": "latitude", "axis": "Y"})
        ds["longitude"].attrs.update({"units": "degrees_east", "standard_name": "longitude", "axis": "X"})

    # Replace NaN with fill value and set _FillValue attribute
    for var in ds.data_vars:
        if ds[var].dtype in (np.float32, np.float64):
            ds[var] = ds[var].fillna(FILL_VALUE)
            ds[var].attrs["_FillValue"] = FILL_VALUE
            ds[var].attrs["missing_value"] = FILL_VALUE
    return ds


def load_datasets() -> dict:
    datasets = {}

    # 1. Load features from Zarr
    features_zarr = os.path.join(ZARR_DIR, "features.zarr")
    if os.path.isdir(features_zarr):
        print("Loading features from Zarr...")
        ds_features = xr.open_zarr(features_zarr)
        ds_features.load()
        ds_features = _make_cf(ds_features)

        for month in range(1, 13):
            ds_m = ds_features.sel(month=month, drop=True)
            for var in ds_m.data_vars:
                datasets["%s_m%02d" % (var, month)] = ds_m[[var]]
                if month == 1:
                    datasets[var] = ds_m[[var]]
        print("  Loaded %d datasets from features" % (len(datasets)))

    # 2. Fallback: load from NetCDF
    elif os.path.isdir(FEATURES_DIR):
        print("Loading features from NetCDF...")
        files = sorted(glob.glob(os.path.join(FEATURES_DIR, "features_month*_src50m.nc")))
        for fpath in files:
            month_str = os.path.basename(fpath).replace("features_month", "").replace("_src50m.nc", "")
            ds = xr.open_dataset(fpath)
            ds = _make_cf(ds)
            ds.load()
            for var in ds.data_vars:
                datasets["%s_m%s" % (var, month_str)] = ds[[var]]
                if month_str == "01":
                    datasets[var] = ds[[var]]

    # 3. WOA23 SST
    t_path = os.path.join(WOA23_DIR, "temperature", "woa23_decav91C0_t01_04.nc")
    if os.path.exists(t_path):
        ds_t = xr.open_dataset(t_path, decode_times=False)
        ds_sst = ds_t[["t_an"]].isel(depth=0, time=0, drop=True)
        ds_sst = ds_sst.rename({"t_an": "sea_surface_temperature"})
        ds_sst = _make_cf(ds_sst)
        ds_sst.load()
        datasets["sst"] = ds_sst

    return datasets


def create_app():
    datasets = load_datasets()
    if not datasets:
        datasets["empty"] = xr.Dataset()

    print("Serving %d WMS datasets" % len(datasets))
    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
