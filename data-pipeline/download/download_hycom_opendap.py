#!/usr/bin/env python3
"""
Download HYCOM GOFS 3.1 T/S data via OPeNDAP.
Downloads daily 12:00Z snapshots as monthly files.
Uses chunked spatial requests to avoid OOM on low-memory servers.

Data source: HYCOM GLBy0.08/expt_93.0 (2018-12 to 2024-09)

Usage:
    python3 download_hycom_opendap.py                     # Default: 2024-01 to 2024-09
    python3 download_hycom_opendap.py 2024 2024 1 6       # 2024 Jan-Jun
    python3 download_hycom_opendap.py 2023 2024            # 2023-2024 all months
"""

import sys
import os
import xarray as xr
import numpy as np
from datetime import datetime
import calendar

GOFS31_URL = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"
OUTPUT_DIR = os.environ.get("HYCOM_OUTPUT_DIR", "/root/ocean_acoustic/hycom")

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def download_day_chunked(ds, year, month, day, outdir):
    """Download a single day by splitting into lat/lon chunks to avoid OOM."""
    date_str = f"{year}{month:02d}{day:02d}"
    outfile = os.path.join(outdir, f"hycom_ts_{date_str}.nc")

    if os.path.exists(outfile):
        size_mb = os.path.getsize(outfile) / 1e6
        if size_mb > 50:
            return "skip"

    target_time = f"{year}-{month:02d}-{day:02d}T12:00:00"

    try:
        # Select nearest time
        ds_snap = ds.sel(time=target_time, method="nearest")

        # Only T/S
        vars_to_keep = [v for v in ["water_temp", "salinity"] if v in ds]
        ds_snap = ds_snap[vars_to_keep]

        # Split latitude into chunks to fit in memory
        # HYCOM lat ~4251 points, split into ~8 chunks of ~530 points each
        lat_vals = ds_snap.lat.values
        chunk_size = 530
        chunks = []

        for i in range(0, len(lat_vals), chunk_size):
            lat_slice = slice(i, min(i + chunk_size, len(lat_vals)))
            chunk = ds_snap.isel(lat=lat_slice).load()
            chunks.append(chunk)

        # Concatenate chunks
        ds_full = xr.concat(chunks, dim="lat")

        # Save
        encoding = {v: {"zlib": True, "complevel": 4} for v in vars_to_keep}
        ds_full.to_netcdf(outfile, encoding=encoding)

        size_mb = os.path.getsize(outfile) / 1e6
        log(f"  {date_str}: {size_mb:.0f}MB")

        # Free memory
        del chunks, ds_full
        return "ok"

    except Exception as e:
        log(f"  FAILED {date_str}: {e}")
        if os.path.exists(outfile):
            os.remove(outfile)
        return "fail"

def main():
    args = sys.argv[1:]
    start_year = int(args[0]) if len(args) > 0 else 2024
    end_year = int(args[1]) if len(args) > 1 else 2024
    start_month = int(args[2]) if len(args) > 2 else 1
    end_month = int(args[3]) if len(args) > 3 else 9

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("=== HYCOM OPeNDAP Download (chunked) ===")
    log(f"Period: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
    log(f"Output: {OUTPUT_DIR}")

    # Open dataset once (metadata only, lazy)
    log("Opening OPeNDAP connection...")
    ds = xr.open_dataset(GOFS31_URL, engine="netcdf4", decode_times=False)

    # Decode time manually (HYCOM uses "hours since analysis")
    base_time = np.datetime64("2000-01-01T00:00:00")
    time_vals = ds.time.values
    time_dt = base_time + (time_vals * 3600 * 1e9).astype("timedelta64[ns]")
    ds = ds.assign_coords(time=time_dt)

    log(f"Time range: {str(time_dt[0])[:10]} to {str(time_dt[-1])[:10]}")
    log(f"Grid: lat={len(ds.lat)}, lon={len(ds.lon)}, depth={len(ds.depth)}")

    success = 0
    failed = 0
    skipped = 0

    for year in range(start_year, end_year + 1):
        m_start = start_month if year == start_year else 1
        m_end = end_month if year == end_year else 12

        if year > 2024 or (year == 2024 and m_start > 9):
            log(f"Skipping {year}: GOFS 3.1 ends 2024-09")
            continue
        if year == 2024:
            m_end = min(m_end, 9)

        for month in range(m_start, m_end + 1):
            days = calendar.monthrange(year, month)[1]
            outdir = os.path.join(OUTPUT_DIR, str(year))
            os.makedirs(outdir, exist_ok=True)

            log(f"--- {year}-{month:02d} ({days} days) ---")

            for day in range(1, days + 1):
                result = download_day_chunked(ds, year, month, day, outdir)
                if result == "ok":
                    success += 1
                elif result == "skip":
                    skipped += 1
                else:
                    failed += 1

            log(f"  Month summary: ok={success}, skip={skipped}, fail={failed}")

    ds.close()
    log("=== HYCOM download complete ===")
    log(f"Success: {success}, Skipped: {skipped}, Failed: {failed}")

    total_size = 0
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if f.endswith('.nc'):
                total_size += os.path.getsize(os.path.join(root, f))
    log(f"Total size: {total_size / 1e9:.1f} GB")

if __name__ == "__main__":
    main()
