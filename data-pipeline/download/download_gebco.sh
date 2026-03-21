#!/bin/bash
# Download GEBCO 2024 global bathymetry grid
# Source: GEBCO (General Bathymetric Chart of the Oceans)
# Resolution: 15 arc-second (~450m)
# Format: NetCDF

set -euo pipefail

BASE_DIR="/data/nas_data/ocean_acoustic/gebco"
mkdir -p "$BASE_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# GEBCO 2024 download URL (NetCDF format)
# The zip file contains GEBCO_2024.nc (~8 GB)
GEBCO_URL="https://www.bodc.ac.uk/data/open_download/gebco/gebco_2024/zip/"
GEBCO_ZIP="${BASE_DIR}/gebco_2024.zip"
GEBCO_NC="${BASE_DIR}/GEBCO_2024.nc"

if [[ -f "$GEBCO_NC" ]]; then
    log "SKIP (exists): GEBCO_2024.nc ($(du -h "$GEBCO_NC" | cut -f1))"
    exit 0
fi

if [[ -f "$GEBCO_ZIP" ]]; then
    log "ZIP exists, skipping download"
else
    log "Downloading GEBCO 2024 (~8 GB)..."
    wget -q --show-progress -c -O "${GEBCO_ZIP}.tmp" "$GEBCO_URL" && mv "${GEBCO_ZIP}.tmp" "$GEBCO_ZIP"
    log "Download complete: $(du -h "$GEBCO_ZIP" | cut -f1)"
fi

log "Extracting..."
cd "$BASE_DIR"
unzip -o "$GEBCO_ZIP" "*.nc"
log "Cleaning up zip..."
rm -f "$GEBCO_ZIP"

log "=== GEBCO download complete ==="
ls -lh "${BASE_DIR}"/*.nc
