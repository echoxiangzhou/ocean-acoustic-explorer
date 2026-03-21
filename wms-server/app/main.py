"""
xpublish-wms server for OceanAcoustic Explorer.

Serves precomputed acoustic features as OGC WMS 1.3.0 tiles.
xpublish-wms requires CF-compliant coordinate names (latitude/longitude)
and 2D DataArrays for rendering.
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


def _make_cf_compliant(ds: xr.Dataset) -> xr.Dataset:
    """Rename lat/lon to latitude/longitude and add CF attributes."""
    if "lat" in ds.dims:
        ds = ds.rename({"lat": "latitude", "lon": "longitude"})
    ds["latitude"].attrs.update({
        "units": "degrees_north",
        "standard_name": "latitude",
        "axis": "Y",
    })
    ds["longitude"].attrs.update({
        "units": "degrees_east",
        "standard_name": "longitude",
        "axis": "X",
    })
    return ds


def load_datasets() -> dict:
    datasets = {}

    # Load precomputed acoustic features
    # Each file: features_monthXX_src50m.nc with (lat=720, lon=1440) and 6 variables
    # Load month 1 as default view (single 2D slice per variable)
    feature_files = sorted(glob.glob(f"{FEATURES_DIR}/features_month*_src50m.nc"))
    if feature_files:
        for fpath in feature_files:
            # Extract month number from filename
            basename = os.path.basename(fpath)
            # features_month01_src50m.nc -> 01
            month_str = basename.replace("features_month", "").replace("_src50m.nc", "")

            ds = xr.open_dataset(fpath)
            ds = _make_cf_compliant(ds)

            # Register each variable as separate dataset (2D, no extra dims)
            for var in ds.data_vars:
                dataset_name = f"{var}_m{month_str}"
                ds_var = ds[[var]]
                datasets[dataset_name] = ds_var

        # Also register month 01 variables with short names (default layer)
        if feature_files:
            ds_default = xr.open_dataset(feature_files[0])
            ds_default = _make_cf_compliant(ds_default)
            for var in ds_default.data_vars:
                datasets[var] = ds_default[[var]]

        print(f"Loaded {len(feature_files)} months of acoustic features")

    # Load WOA23 SST (surface temperature, month 01 as default)
    t_path = f"{WOA23_DIR}/temperature/woa23_decav91C0_t01_04.nc"
    if os.path.exists(t_path):
        ds_t = xr.open_dataset(t_path, decode_times=False)
        ds_sst = ds_t[["t_an"]].isel(depth=0, time=0, drop=True)
        ds_sst = ds_sst.rename({"t_an": "sea_surface_temperature"})
        ds_sst = _make_cf_compliant(ds_sst)
        datasets["sst"] = ds_sst
        print("Loaded WOA23 SST (January)")

    return datasets


def create_app():
    datasets = load_datasets()

    if not datasets:
        print("WARNING: No datasets loaded.")
        datasets["empty"] = xr.Dataset()

    print(f"Serving {len(datasets)} WMS datasets: {list(datasets.keys())[:10]}...")
    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
