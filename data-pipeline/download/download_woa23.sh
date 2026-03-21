#!/bin/bash
# Download WOA23 Temperature and Salinity (0.25° monthly climatology)
# Source: NOAA NCEI THREDDS
# Files: 16 files per variable (months 01-12 + seasons 13-16)
# We only need months 01-12 for this project

set -euo pipefail

BASE_DIR="/data/nas_data/ocean_acoustic/woa23"
BASE_URL="https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA"

mkdir -p "${BASE_DIR}/temperature" "${BASE_DIR}/salinity"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

download_file() {
    local url="$1"
    local dest="$2"
    local filename
    filename=$(basename "$dest")

    if [[ -f "$dest" ]]; then
        log "SKIP (exists): $filename"
        return 0
    fi

    log "Downloading: $filename"
    wget -q --show-progress -c -O "${dest}.tmp" "$url" && mv "${dest}.tmp" "$dest"
    log "Done: $filename ($(du -h "$dest" | cut -f1))"
}

# Download monthly temperature (01-12) at 0.25° resolution
# decav91C0 = decadal average 1991-2020 climatology
# _04 suffix = 0.25 degree grid
log "=== Downloading WOA23 Temperature (0.25°, monthly) ==="
for month in $(seq -w 1 12); do
    url="${BASE_URL}/temperature/netcdf/decav91C0/0.25/woa23_decav91C0_t${month}_04.nc"
    dest="${BASE_DIR}/temperature/woa23_decav91C0_t${month}_04.nc"
    download_file "$url" "$dest"
done

# Download monthly salinity (01-12) at 0.25° resolution
log "=== Downloading WOA23 Salinity (0.25°, monthly) ==="
for month in $(seq -w 1 12); do
    url="${BASE_URL}/salinity/netcdf/decav91C0/0.25/woa23_decav91C0_s${month}_04.nc"
    dest="${BASE_DIR}/salinity/woa23_decav91C0_s${month}_04.nc"
    download_file "$url" "$dest"
done

# Also download annual mean (month 00) for reference
log "=== Downloading WOA23 Annual Mean ==="
download_file "${BASE_URL}/temperature/netcdf/decav91C0/0.25/woa23_decav91C0_t00_04.nc" \
    "${BASE_DIR}/temperature/woa23_decav91C0_t00_04.nc"
download_file "${BASE_URL}/salinity/netcdf/decav91C0/0.25/woa23_decav91C0_s00_04.nc" \
    "${BASE_DIR}/salinity/woa23_decav91C0_s00_04.nc"

log "=== WOA23 download complete ==="
du -sh "${BASE_DIR}/temperature" "${BASE_DIR}/salinity"
