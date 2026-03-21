#!/usr/bin/env python3
"""
Download HYCOM GOFS 3.1 T/S via OPeNDAP locally, pipe directly to ocean-server.
No local disk storage - streams NetCDF through SSH pipe.

HYCOM GLBy0.08/expt_93.0:
  - Variables: water_temp (in-situ °C), salinity (PSU)
  - 40 depth levels: 0-5000m
  - Grid: 0.08° lon x 0.04° lat
  - Time: 2018-12-04 to 2024-09-05

Usage:
    python3 relay_hycom.py                    # Default: 2024-01 to 2024-09
    python3 relay_hycom.py 2024 2024 6 9      # 2024 Jun-Sep
    python3 relay_hycom.py 2023 2024           # 2023-2024
"""

import sys
import os
import subprocess
import tempfile
import xarray as xr
import numpy as np
from datetime import datetime
import calendar

GOFS31_URL = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"
REMOTE_DIR = "/data/nas_data/ocean_acoustic/hycom"
SSH_HOST = "ocean-server"


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def download_and_relay_day(ds, year, month, day):
    """Download one day from OPeNDAP and pipe to ocean-server."""
    date_str = "%d%02d%02d" % (year, month, day)
    remote_path = "%s/%d/hycom_ts_%s.nc" % (REMOTE_DIR, year, date_str)

    # Check if already exists on remote
    check = subprocess.run(
        ["ssh", SSH_HOST, "test -s '%s' && echo EXISTS" % remote_path],
        capture_output=True, text=True, timeout=10
    )
    if "EXISTS" in check.stdout:
        return "skip"

    target_time = "%d-%02d-%02dT12:00:00" % (year, month, day)

    try:
        # Select single time snapshot, only T/S
        ds_snap = ds[["water_temp", "salinity"]].sel(time=target_time, method="nearest")

        # Write to temp file, then pipe to remote
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=True) as tmp:
            tmp_path = tmp.name

        # Load data into memory
        ds_snap.load()

        # Save to temp file with compression
        encoding = {
            "water_temp": {"zlib": True, "complevel": 4, "dtype": "float32"},
            "salinity": {"zlib": True, "complevel": 4, "dtype": "float32"},
        }
        ds_snap.to_netcdf(tmp_path, encoding=encoding)

        size_mb = os.path.getsize(tmp_path) / 1e6

        # Ensure remote directory exists
        subprocess.run(
            ["ssh", SSH_HOST, "mkdir -p '%s/%d'" % (REMOTE_DIR, year)],
            timeout=10
        )

        # SCP to ocean-server
        result = subprocess.run(
            ["scp", "-q", tmp_path, "%s:%s" % (SSH_HOST, remote_path)],
            timeout=300
        )

        # Clean up temp file
        os.unlink(tmp_path)

        if result.returncode == 0:
            log("  %s: %.0fMB -> ocean-server" % (date_str, size_mb))
            del ds_snap
            return "ok"
        else:
            log("  %s: SCP failed" % date_str)
            del ds_snap
            return "fail"

    except Exception as e:
        log("  FAILED %s: %s" % (date_str, str(e)))
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return "fail"


def main():
    args = sys.argv[1:]
    start_year = int(args[0]) if len(args) > 0 else 2024
    end_year = int(args[1]) if len(args) > 1 else 2024
    start_month = int(args[2]) if len(args) > 2 else 1
    end_month = int(args[3]) if len(args) > 3 else 9

    log("=== HYCOM Relay: local OPeNDAP -> ocean-server ===")
    log("Period: %d-%02d to %d-%02d" % (start_year, start_month, end_year, end_month))

    # Open dataset (metadata only, lazy)
    log("Opening OPeNDAP connection...")
    ds = xr.open_dataset(GOFS31_URL, engine="netcdf4", decode_times=False)

    # Decode time
    base_time = np.datetime64("2000-01-01T00:00:00")
    time_vals = ds.time.values
    time_dt = base_time + (time_vals * 3600 * 1e9).astype("timedelta64[ns]")
    ds = ds.assign_coords(time=time_dt)
    log("Time range: %s to %s" % (str(time_dt[0])[:10], str(time_dt[-1])[:10]))
    log("Grid: lat=%d, lon=%d, depth=%d" % (len(ds.lat), len(ds.lon), len(ds.depth)))

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
            days = calendar.monthrange(year, month)[1]
            log("--- %d-%02d (%d days) ---" % (year, month, days))

            for day in range(1, days + 1):
                result = download_and_relay_day(ds, year, month, day)
                if result == "ok":
                    success += 1
                elif result == "skip":
                    skipped += 1
                else:
                    failed += 1

            log("  Month done: ok=%d skip=%d fail=%d" % (success, skipped, failed))

    ds.close()
    log("=== Complete: ok=%d, skip=%d, fail=%d ===" % (success, skipped, failed))


if __name__ == "__main__":
    main()
