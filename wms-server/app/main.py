"""
xpublish-wms server for OceanAcoustic Explorer.

Loads WOA23 sound speed and feature Zarr datasets,
serves them as OGC WMS 1.3.0 tile layers.

Data loaded from /data directory (mounted from NAS).
"""

import os
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

DATA_DIR = os.getenv("DATA_DIR", "/data")
WOA23_DIR = os.getenv("WOA23_DIR", f"{DATA_DIR}/woa23")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))


def load_datasets() -> dict:
    """Load all datasets for xpublish to serve via WMS."""
    datasets = {}

    # Load WOA23 temperature (all 12 months merged)
    # Each month file has t_an with dims (time=1, depth=57, lat=720, lon=1440)
    t_files = sorted(
        [f"{WOA23_DIR}/temperature/woa23_decav91C0_t{m:02d}_04.nc" for m in range(1, 13)]
    )
    existing_t = [f for f in t_files if os.path.exists(f)]
    if existing_t:
        ds_list = [xr.open_dataset(f, decode_times=False) for f in existing_t]
        ds_temp = xr.concat(ds_list, dim="time")
        ds_temp["time"] = list(range(1, len(ds_list) + 1))
        datasets["woa23_temperature"] = ds_temp
        print(f"Loaded WOA23 temperature: {len(existing_t)} months")

    # Load WOA23 salinity
    s_files = sorted(
        [f"{WOA23_DIR}/salinity/woa23_decav91C0_s{m:02d}_04.nc" for m in range(1, 13)]
    )
    existing_s = [f for f in s_files if os.path.exists(f)]
    if existing_s:
        ds_list = [xr.open_dataset(f, decode_times=False) for f in existing_s]
        ds_salt = xr.concat(ds_list, dim="time")
        ds_salt["time"] = list(range(1, len(ds_list) + 1))
        datasets["woa23_salinity"] = ds_salt
        print(f"Loaded WOA23 salinity: {len(existing_s)} months")

    # Load precomputed feature Zarr datasets if they exist
    features_dir = f"{DATA_DIR}/features"
    if os.path.isdir(features_dir):
        for name in os.listdir(features_dir):
            if name.endswith(".zarr"):
                feature_name = name.replace(".zarr", "")
                ds = xr.open_zarr(f"{features_dir}/{name}")
                datasets[feature_name] = ds
                print(f"Loaded feature: {feature_name}")

    # Load GEBCO bathymetry if exists (large, load lazily)
    gebco_path = f"{DATA_DIR}/gebco/GEBCO_2024.nc"
    if os.path.exists(gebco_path):
        datasets["bathymetry"] = xr.open_dataset(gebco_path)
        print("Loaded GEBCO bathymetry")

    return datasets


def create_app():
    datasets = load_datasets()

    if not datasets:
        print("WARNING: No datasets loaded. Check DATA_DIR and file paths.")
        # Create a dummy dataset so the server starts
        datasets["empty"] = xr.Dataset()

    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
