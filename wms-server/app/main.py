"""
xpublish-wms server for OceanAcoustic Explorer.

Loads data from Zarr stores for fast random access tile serving.
"""

import os
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

ZARR_DIR = os.getenv("ZARR_DIR", "/data/zarr")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))


def load_datasets() -> dict:
    datasets = {}

    # Load features from Zarr (12 months x 6 variables)
    features_path = os.path.join(ZARR_DIR, "features.zarr")
    if os.path.isdir(features_path):
        ds_features = xr.open_zarr(features_path)
        # Register each month×variable as separate 2D dataset for WMS
        for month in range(1, 13):
            ds_month = ds_features.sel(month=month, drop=True)
            for var in ds_month.data_vars:
                name = "%s_m%02d" % (var, month)
                datasets[name] = ds_month[[var]]
            # Default (short name) = month 1
            if month == 1:
                for var in ds_month.data_vars:
                    datasets[var] = ds_month[[var]]
        print("Loaded features.zarr: 12 months x %d vars" % len(ds_features.data_vars))

    # Load WOA23 SST from Zarr (surface layer, month 1 default)
    temp_path = os.path.join(ZARR_DIR, "woa23_temperature.zarr")
    if os.path.isdir(temp_path):
        ds_t = xr.open_zarr(temp_path)
        ds_sst = ds_t[["t_an"]].sel(month=1, depth=0.0, drop=True)
        ds_sst = ds_sst.rename({"t_an": "sea_surface_temperature"})
        datasets["sst"] = ds_sst
        print("Loaded woa23_temperature.zarr (SST)")

    # Load GEBCO coarsened from Zarr
    gebco_path = os.path.join(ZARR_DIR, "gebco_coarse.zarr")
    if os.path.isdir(gebco_path):
        datasets["bathymetry"] = xr.open_zarr(gebco_path)
        print("Loaded gebco_coarse.zarr")

    return datasets


def create_app():
    datasets = load_datasets()
    if not datasets:
        print("WARNING: No datasets loaded. Check ZARR_DIR=%s" % ZARR_DIR)
        datasets["empty"] = xr.Dataset()

    print("Serving %d WMS datasets" % len(datasets))
    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
