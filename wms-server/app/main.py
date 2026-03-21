"""
xpublish-wms server for OceanAcoustic Explorer.

Serves WOA23 T/S and precomputed acoustic features as OGC WMS 1.3.0 tiles.
Data loaded from /data directory (mounted from NAS).

Precomputed features (verified format):
  - files: features_month{01-12}_src50m.nc
  - variables: channel_axis_depth, surface_duct, thermocline_gradient,
               convergence_zone_km, shadow_zone_km, field_type
  - dims: (lat=720, lon=1440), 0.25°
"""

import os
import glob
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

DATA_DIR = os.getenv("DATA_DIR", "/data")
WOA23_DIR = os.getenv("WOA23_DIR", f"{DATA_DIR}/woa23")
FEATURES_DIR = os.getenv("FEATURES_DIR", f"{DATA_DIR}/features")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))


def load_datasets() -> dict:
    datasets = {}

    # Load precomputed acoustic features (one dataset per month)
    feature_files = sorted(glob.glob(f"{FEATURES_DIR}/features_month*_src50m.nc"))
    if feature_files:
        ds_list = []
        for f in feature_files:
            ds = xr.open_dataset(f)
            ds_list.append(ds)

        # Merge all months into single dataset with month dimension
        ds_features = xr.concat(ds_list, dim="month")
        ds_features["month"] = list(range(1, len(ds_list) + 1))

        # Register each variable as a separate WMS layer
        for var in ["channel_axis_depth", "surface_duct", "thermocline_gradient",
                     "convergence_zone_km", "shadow_zone_km", "field_type"]:
            if var in ds_features:
                datasets[var] = ds_features[[var]]

        print(f"Loaded {len(feature_files)} months of acoustic features")
        print(f"  Feature layers: {list(ds_features.data_vars)}")

    # Load WOA23 temperature (surface layer only for WMS overview)
    t_files = sorted(
        [f"{WOA23_DIR}/temperature/woa23_decav91C0_t{m:02d}_04.nc" for m in range(1, 13)]
    )
    existing_t = [f for f in t_files if os.path.exists(f)]
    if existing_t:
        ds_list = []
        for f in existing_t:
            ds = xr.open_dataset(f, decode_times=False)
            # Take surface (depth=0) and first depth layers for WMS
            ds_surf = ds[["t_an"]].isel(depth=0, time=0, drop=True)
            ds_surf = ds_surf.rename({"t_an": "sst"})
            ds_list.append(ds_surf)

        ds_sst = xr.concat(ds_list, dim="month")
        ds_sst["month"] = list(range(1, len(ds_list) + 1))
        datasets["sea_surface_temperature"] = ds_sst
        print(f"Loaded WOA23 SST: {len(existing_t)} months")

    # Load WOA23 salinity (surface)
    s_files = sorted(
        [f"{WOA23_DIR}/salinity/woa23_decav91C0_s{m:02d}_04.nc" for m in range(1, 13)]
    )
    existing_s = [f for f in s_files if os.path.exists(f)]
    if existing_s:
        ds_list = []
        for f in existing_s:
            ds = xr.open_dataset(f, decode_times=False)
            ds_surf = ds[["s_an"]].isel(depth=0, time=0, drop=True)
            ds_surf = ds_surf.rename({"s_an": "sss"})
            ds_list.append(ds_surf)

        ds_sss = xr.concat(ds_list, dim="month")
        ds_sss["month"] = list(range(1, len(ds_list) + 1))
        datasets["sea_surface_salinity"] = ds_sss
        print(f"Loaded WOA23 SSS: {len(existing_s)} months")

    return datasets


def create_app():
    datasets = load_datasets()

    if not datasets:
        print("WARNING: No datasets loaded. Check DATA_DIR and file paths.")
        datasets["empty"] = xr.Dataset()

    print(f"Serving {len(datasets)} WMS datasets: {list(datasets.keys())}")
    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
