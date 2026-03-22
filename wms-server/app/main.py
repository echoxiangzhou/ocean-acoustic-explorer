"""
xpublish-wms server for OceanAcoustic Explorer.
Preloads CF-compliant feature data into memory.
"""

import os
import glob
import xarray as xr
import xpublish
from xpublish_wms import CfWmsPlugin

FEATURES_DIR = os.getenv("FEATURES_DIR", "/data/features")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))


def load_datasets() -> dict:
    datasets = {}

    files = sorted(glob.glob(os.path.join(FEATURES_DIR, "features_month*_src50m.nc")))
    if not files:
        print("WARNING: No feature files found in %s" % FEATURES_DIR)
        return datasets

    print("Loading %d feature files..." % len(files))
    for fpath in files:
        month_str = os.path.basename(fpath).replace("features_month", "").replace("_src50m.nc", "")
        ds = xr.open_dataset(fpath)
        ds.load()

        # Register each variable as separate WMS dataset
        for var in ds.data_vars:
            name = "%s_m%s" % (var, month_str)
            datasets[name] = ds[[var]]
            if month_str == "01":
                datasets[var] = ds[[var]]

    print("Loaded %d WMS datasets" % len(datasets))
    return datasets


def create_app():
    datasets = load_datasets()
    if not datasets:
        datasets["empty"] = xr.Dataset()

    rest = xpublish.Rest(datasets, plugins={"wms": CfWmsPlugin()})
    return rest.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
