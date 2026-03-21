"""
Unified data reader for all ocean datasets.

Verified data formats:
  WOA23:  t_an/s_an, (time=1, depth=57, lat=720, lon=1440), 0.25°, decode_times=False
  HYCOM:  water_temp/salinity, (time, depth=40, lat, lon), 0.08°, in-situ temperature
  SODA:   temp/salt, (time=1, depth=50, lat=330, lon=720), 0.5°, potential temperature
  GEBCO:  elevation (int16), (lat=43200, lon=86400), 15 arc-second
"""

import numpy as np
import xarray as xr
import gsw
from functools import lru_cache
from pathlib import Path
from app.config import WOA23_DIR, HYCOM_DIR, SODA_DIR

# HYCOM 40 standard depth levels (meters) - verified from Google Earth Engine docs
HYCOM_DEPTHS = [
    0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50,
    60, 70, 80, 90, 100, 125, 150, 200, 250, 300, 350, 400,
    500, 600, 700, 800, 900, 1000, 1250, 1500, 2000, 2500, 3000, 4000, 5000,
]

# SODA 3.15.2 50 depth levels (meters) - verified from .ctl file
SODA_DEPTHS = [
    5.03, 15.10, 25.22, 35.36, 45.58, 55.86, 66.26, 76.80, 87.58, 98.62,
    110.10, 122.11, 134.91, 148.75, 164.05, 181.31, 201.26, 224.78, 253.07, 287.55,
    330.01, 382.37, 446.73, 525.0, 618.70, 728.69, 855.0, 996.72, 1152.4, 1320.0,
    1497.6, 1683.1, 1874.8, 2071.3, 2271.3, 2474.0, 2678.8, 2884.9, 3092.1, 3300.1,
    3508.6, 3717.6, 3926.8, 4136.3, 4345.9, 4555.6, 4765.4, 4975.2, 5185.1, 5395.0,
]

# WOA23 57 depth levels (meters) - verified from actual data
WOA23_DEPTHS = [
    0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95,
    100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400, 425, 450, 475,
    500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200,
    1250, 1300, 1350, 1400, 1450, 1500,
]


@lru_cache(maxsize=24)
def load_woa23_month(month: int) -> tuple:
    """
    Load WOA23 T/S for a given month.

    Returns (ds_temp, ds_salt) xarray Datasets.
    Variables: t_an (temperature °C), s_an (salinity PSU).
    Must use decode_times=False due to "months since" time units.
    """
    month_str = str(month).zfill(2)
    t_path = f"{WOA23_DIR}/temperature/woa23_decav91C0_t{month_str}_04.nc"
    s_path = f"{WOA23_DIR}/salinity/woa23_decav91C0_s{month_str}_04.nc"
    ds_t = xr.open_dataset(t_path, decode_times=False)
    ds_s = xr.open_dataset(s_path, decode_times=False)
    return ds_t, ds_s


def read_woa23_profile(lat: float, lon: float, month: int) -> dict:
    """
    Read T/S profile from WOA23 at nearest grid point.

    Returns dict with depth, temperature (°C in-situ), salinity (PSU),
    and actual lat/lon of the grid point.
    """
    ds_t, ds_s = load_woa23_month(month)

    lat_idx = int(np.abs(ds_t.lat.values - lat).argmin())
    lon_idx = int(np.abs(ds_t.lon.values - lon).argmin())

    temp = ds_t["t_an"].values[0, :, lat_idx, lon_idx]  # (57,)
    salt = ds_s["s_an"].values[0, :, lat_idx, lon_idx]  # (57,)
    depth = ds_t["depth"].values  # (57,)

    valid = ~np.isnan(temp) & ~np.isnan(salt)

    return {
        "depth": depth[valid],
        "temperature": temp[valid],
        "salinity": salt[valid],
        "lat": float(ds_t.lat.values[lat_idx]),
        "lon": float(ds_t.lon.values[lon_idx]),
        "source": "woa23",
        "temp_type": "in_situ",  # WOA23 stores in-situ temperature
    }


def read_hycom_profile(lat: float, lon: float, date_str: str) -> dict:
    """
    Read T/S profile from local HYCOM data.

    HYCOM variables: water_temp (in-situ °C), salinity (PSU).
    40 depth levels: 0-5000m.

    Args:
        date_str: YYYYMMDD format, e.g. "20240101"
    """
    year = date_str[:4]
    nc_path = Path(HYCOM_DIR) / year / f"hycom_ts_{date_str}.nc"

    if not nc_path.exists():
        raise FileNotFoundError(f"HYCOM data not found: {nc_path}")

    ds = xr.open_dataset(str(nc_path))

    lat_idx = int(np.abs(ds.lat.values - lat).argmin())
    lon_idx = int(np.abs(ds.lon.values - lon).argmin())

    temp = ds["water_temp"].values[:, lat_idx, lon_idx]  # (40,)
    salt = ds["salinity"].values[:, lat_idx, lon_idx]    # (40,)
    depth = ds["depth"].values if "depth" in ds else np.array(HYCOM_DEPTHS)

    valid = ~np.isnan(temp) & ~np.isnan(salt)

    ds.close()

    return {
        "depth": depth[valid],
        "temperature": temp[valid],
        "salinity": salt[valid],
        "lat": float(ds.lat.values[lat_idx]),
        "lon": float(ds.lon.values[lon_idx]),
        "source": "hycom",
        "temp_type": "in_situ",  # HYCOM provides in-situ temperature
    }


def read_soda_profile(lat: float, lon: float, date_str: str) -> dict:
    """
    Read T/S profile from SODA 3.15.2 data.

    SODA variables: temp (potential temperature °C), salt (PSU).
    50 depth levels: 5-5395m, 0.5° grid.
    File naming: soda3.15.2_5dy_ocean_reg_YYYY_MM_DD.nc

    Note: SODA stores POTENTIAL temperature, not in-situ.
    Must convert to in-situ for sound speed calculation.

    Args:
        date_str: YYYY_MM_DD format, e.g. "1990_06_03"
    """
    year = date_str[:4]
    filename = f"soda3.15.2_5dy_ocean_reg_{date_str}.nc"
    nc_path = Path(SODA_DIR) / year / filename

    if not nc_path.exists():
        raise FileNotFoundError(f"SODA data not found: {nc_path}")

    ds = xr.open_dataset(str(nc_path), decode_times=False)

    # SODA lon starts at 0.25, range 0-360. Convert query lon if needed.
    query_lon = lon if lon >= 0 else lon + 360.0

    lat_idx = int(np.abs(ds.lat.values - lat).argmin())
    lon_idx = int(np.abs(ds.lon.values - query_lon).argmin())

    # SODA dims: (time=1, lev=50, lat=330, lon=720)
    pot_temp = ds["temp"].values[0, :, lat_idx, lon_idx]  # potential temperature
    salt = ds["salt"].values[0, :, lat_idx, lon_idx]
    depth = np.array(SODA_DEPTHS)

    valid = ~np.isnan(pot_temp) & ~np.isnan(salt)

    ds.close()

    return {
        "depth": depth[valid],
        "temperature": pot_temp[valid],
        "salinity": salt[valid],
        "lat": float(ds.lat.values[lat_idx]),
        "lon": float(ds.lon.values[lon_idx]),
        "source": "soda",
        "temp_type": "potential",  # SODA stores potential temperature
    }


def potential_to_insitu(pot_temp: np.ndarray, salinity: np.ndarray,
                        depth: np.ndarray, lat: float, lon: float) -> np.ndarray:
    """
    Convert potential temperature to in-situ temperature using TEOS-10 (gsw).
    Required for SODA data before sound speed calculation.
    """
    pressure = gsw.p_from_z(-depth, lat)
    sa = gsw.SA_from_SP(salinity, pressure, lon, lat)
    # gsw.t_from_CT requires conservative temperature, but SODA gives potential temp
    # For potential temp -> in-situ: use gsw.t_from_CT after converting
    ct = gsw.CT_from_pt(sa, pot_temp)
    t_insitu = gsw.t_from_CT(sa, ct, pressure)
    return t_insitu
