"""
Custom WMS-compatible tile endpoint with correct NaN transparency.
Replaces xpublish-wms for feature layer rendering.
"""

import io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from fastapi import APIRouter, Query
from fastapi.responses import Response
from functools import lru_cache
import xarray as xr
import os

router = APIRouter()

DATA_DIR = os.getenv("DATA_DIR", "/data")
FEATURES_DIR = os.path.join(DATA_DIR, "features")

# Cache loaded feature data in memory
_feature_cache = {}


def _load_features():
    """Load all feature NetCDF files into memory."""
    if _feature_cache:
        return _feature_cache

    import glob
    files = sorted(glob.glob(os.path.join(FEATURES_DIR, "features_month*_src50m.nc")))
    for fpath in files:
        basename = os.path.basename(fpath)
        month_str = basename.replace("features_month", "").replace("_src50m.nc", "")
        month = int(month_str)

        ds = xr.open_dataset(fpath)
        ds.load()
        _feature_cache[month] = ds

    if _feature_cache:
        print("Tile server: loaded %d months of features" % len(_feature_cache))
    return _feature_cache


LAYER_COLORMAPS = {
    "channel_axis_depth": ("viridis", 0, 1500),
    "surface_duct": ("plasma", 0, 300),
    "thermocline_gradient": ("inferno", 0, 0.5),
    "convergence_zone_km": ("turbo", 20, 80),
    "shadow_zone_km": ("magma", 0, 50),
    "field_type": ("tab10", 0, 4),
}


@router.get("/tiles/wms")
async def get_wms_tile(
    service: str = Query("WMS"),
    request: str = Query("GetMap"),
    layers: str = Query(...),
    bbox: str = Query(...),
    width: int = Query(256),
    height: int = Query(256),
    srs: str = Query("EPSG:4326"),
    format: str = Query("image/png"),
    month: int = Query(1, ge=1, le=12),
    colorscalerange: str = Query(None),
    styles: str = Query(""),
    version: str = Query("1.1.1"),
    transparent: str = Query("true"),
):
    """WMS-compatible GetMap endpoint with correct NaN transparency."""
    cache = _load_features()

    if month not in cache:
        return Response(content=_empty_tile(width, height), media_type="image/png")

    ds = cache[month]

    # Parse layer name (remove month suffix if present)
    layer = layers.split(",")[0]
    if layer not in ds.data_vars:
        return Response(content=_empty_tile(width, height), media_type="image/png")

    # Parse bbox: minx,miny,maxx,maxy (lon,lat for 1.1.1)
    parts = [float(x) for x in bbox.split(",")]
    minx, miny, maxx, maxy = parts

    # Get data for bbox
    data = ds[layer].values  # (720, 1440)
    lat = ds["lat"].values
    lon = ds["lon"].values

    # Find indices for bbox
    lat_mask = (lat >= miny) & (lat <= maxy)
    lon_mask = (lon >= minx) & (lon <= maxx)

    if not lat_mask.any() or not lon_mask.any():
        return Response(content=_empty_tile(width, height), media_type="image/png")

    sub = data[np.ix_(lat_mask, lon_mask)]

    # Colormap and range
    if layer in LAYER_COLORMAPS:
        cmap_name, default_vmin, default_vmax = LAYER_COLORMAPS[layer]
    else:
        cmap_name, default_vmin, default_vmax = "viridis", 0, 1

    if colorscalerange:
        try:
            vmin, vmax = [float(x) for x in colorscalerange.split(",")]
        except ValueError:
            vmin, vmax = default_vmin, default_vmax
    else:
        vmin, vmax = default_vmin, default_vmax

    # Render tile with matplotlib
    png_bytes = _render_tile(sub, width, height, cmap_name, vmin, vmax)

    return Response(content=png_bytes, media_type="image/png")


def _render_tile(data: np.ndarray, width: int, height: int,
                 cmap_name: str, vmin: float, vmax: float) -> bytes:
    """Render 2D array to PNG with NaN as transparent."""
    # Create RGBA image
    cmap = plt.get_cmap(cmap_name)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    # Normalize data
    normalized = norm(data)

    # Apply colormap -> RGBA
    rgba = cmap(normalized)  # shape (h, w, 4) float 0-1

    # Set NaN pixels to fully transparent
    nan_mask = np.isnan(data)
    rgba[nan_mask, 3] = 0.0

    # Convert to uint8
    rgba_uint8 = (rgba * 255).astype(np.uint8)

    # Flip vertically (lat goes from -90 to 90, image from top to bottom)
    rgba_uint8 = rgba_uint8[::-1]

    # Resize to target dimensions
    from PIL import Image
    img = Image.fromarray(rgba_uint8, 'RGBA')
    img = img.resize((width, height), Image.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _empty_tile(width: int, height: int) -> bytes:
    """Generate fully transparent PNG tile."""
    from PIL import Image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
