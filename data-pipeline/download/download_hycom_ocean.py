#!/usr/bin/env python3
"""
Download HYCOM GOFS 3.1 T/S data via OPeNDAP on ocean-server (250G RAM).
Downloads daily 12:00Z snapshots, saves as monthly NetCDF files.

HYCOM GLBy0.08/expt_93.0 verified format:
  - Variables: water_temp (in-situ °C), salinity (PSU)
  - 40 depth levels: 0-5000m
  - Grid: 0.08° lon x 0.04° lat, 80.48°S to 80.48°N
  - Time: 2018-12-04 to 2024-09-05, 3-hourly
  - Time encoding: "hours since analysis" (base 2000-01-01)

Usage:
    python3 download_hycom_ocean.py                   # Default: 2023-01 to 2024-09
    python3 download_hycom_ocean.py 2024 2024 6 9     # 2024 Jun-Sep
"""

import sys
import os
import xarray as xr
import numpy as np
from datetime import datetime
import calendar

GOFS31_URL = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"
OUTPUT_DIR = "/data/nas_data/ocean_acoustic/hycom"

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)

def download_month(ds, year, month):
    """Download all daily 12:00Z snapshots for one month, save as single file."""
    outfile = os.path.join(OUTPUT_DIR, "%d" % year, "hycom_ts_%d%02d.nc" % (year, month))

    if os.path.exists(outfile):
        size_mb = os.path.getsize(outfile) / 1e6
        if size_mb > 500:
            log("SKIP (exists, %.0fMB): %s" % (size_mb, outfile))
            return "skip"

    days = calendar.monthrange(year, month)[1]
    start = "%d-%02d-01T12:00:00" % (year, month)
    if month == 12:
        end = "%d-01-01T00:00:00" % (year + 1)
    else:
        end = "%d-%02d-01T00:00:00" % (year, month + 1)

    try:
        # Select time range
        ds_month = ds.sel(time=slice(start, end))

        # Filter to ~12:00Z (every 4th step from 3-hourly)
        times = ds_month.time.values
        noon_times = []
        for t in times:
            hour = int((t - t.astype("datetime64[D]")) / np.timedelta64(1, "h"))
            if 11 <= hour <= 13:
                noon_times.append(t)
        if not noon_times:
            noon_times = list(times[::4]) if len(times) > 4 else list(times)

        log("  %d-%02d: %d daily snapshots" % (year, month, len(noon_times)))
        ds_daily = ds_month[["water_temp", "salinity"]].sel(time=noon_times)

        # Load into memory (ocean-server has 250G RAM, single month is ~15-20GB)
        log("  Fetching from OPeNDAP...")
        ds_daily.load()

        # Save with compression
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        encoding = {
            "water_temp": {"zlib": True, "complevel": 4, "dtype": "float32"},
            "salinity": {"zlib": True, "complevel": 4, "dtype": "float32"},
        }
        ds_daily.to_netcdf(outfile, encoding=encoding)
        size_mb = os.path.getsize(outfile) / 1e6
        log("  Saved: %s (%.0fMB)" % (outfile, size_mb))

        del ds_daily
        return "ok"

    except Exception as e:
        log("  FAILED %d-%02d: %s" % (year, month, str(e)))
        if os.path.exists(outfile):
            os.remove(outfile)
        return "fail"

def main():
    args = sys.argv[1:]
    start_year = int(args[0]) if len(args) > 0 else 2023
    end_year = int(args[1]) if len(args) > 1 else 2024
    start_month = int(args[2]) if len(args) > 2 else 1
    end_month = int(args[3]) if len(args) > 3 else 9

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("=== HYCOM OPeNDAP Download (ocean-server) ===")
    log("Period: %d-%02d to %d-%02d" % (start_year, start_month, end_year, end_month))
    log("Output: %s" % OUTPUT_DIR)

    # Open dataset (metadata only)
    log("Opening OPeNDAP connection...")
    ds = xr.open_dataset(GOFS31_URL, engine="netcdf4", decode_times=False)

    # Decode time: "hours since analysis" -> actual datetime
    base_time = np.datetime64("2000-01-01T00:00:00")
    time_vals = ds.time.values
    time_dt = base_time + (time_vals * 3600 * 1e9).astype("timedelta64[ns]")
    ds = ds.assign_coords(time=time_dt)
    log("Time range: %s to %s" % (str(time_dt[0])[:10], str(time_dt[-1])[:10]))

    success = 0
    failed = 0
    skipped = 0

    for year in range(start_year, end_year + 1):
        m_start = start_month if year == start_year else 1
        m_end = end_month if year == end_year else 12
        if year > 2024 or (year == 2024 and m_start > 9):
            continue
        if year == 2024:
            m_end = min(m_end, 9)

        for month in range(m_start, m_end + 1):
            result = download_month(ds, year, month)
            if result == "ok":
                success += 1
            elif result == "skip":
                skipped += 1
            else:
                failed += 1

    ds.close()
    log("=== Complete: ok=%d, skip=%d, fail=%d ===" % (success, skipped, failed))

    total_size = 0
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if f.endswith(".nc"):
                total_size += os.path.getsize(os.path.join(root, f))
    log("Total size: %.1f GB" % (total_size / 1e9))

if __name__ == "__main__":
    main()
