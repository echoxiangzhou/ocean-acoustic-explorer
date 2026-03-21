#!/bin/bash
# Download deck41 seafloor sediment data
# Source: NOAA NGDC (National Geophysical Data Center)
# Contains: sediment type, grain size, porosity etc.
# Used for: bottom boundary conditions in acoustic models

set -euo pipefail

BASE_DIR="/data/nas_data/ocean_acoustic/deck41"
mkdir -p "$BASE_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# deck41 surficial sediment data
# Available from NOAA NCEI as point data (CSV) or gridded products
DECK41_URL="https://www.ngdc.noaa.gov/mgg/geology/data/g02889/deck41.csv.gz"
DECK41_DEST="${BASE_DIR}/deck41.csv.gz"

if [[ -f "${BASE_DIR}/deck41.csv" ]] || [[ -f "$DECK41_DEST" ]]; then
    log "SKIP (exists): deck41 data"
else
    log "Downloading deck41 sediment data..."
    wget -q --show-progress -c -O "${DECK41_DEST}.tmp" "$DECK41_URL" && \
        mv "${DECK41_DEST}.tmp" "$DECK41_DEST"
    log "Download complete: $(du -h "$DECK41_DEST" | cut -f1)"
fi

# Extract if compressed
if [[ -f "$DECK41_DEST" ]] && [[ ! -f "${BASE_DIR}/deck41.csv" ]]; then
    log "Extracting..."
    gunzip -k "$DECK41_DEST"
fi

# Also download the gridded sediment thickness from NOAA
SEDTHICK_URL="https://www.ngdc.noaa.gov/mgg/sedthick/data/version3/GlobSed-v3.nc"
SEDTHICK_DEST="${BASE_DIR}/GlobSed-v3.nc"

if [[ -f "$SEDTHICK_DEST" ]]; then
    log "SKIP (exists): GlobSed-v3.nc"
else
    log "Downloading GlobSed v3 (global sediment thickness)..."
    wget -q --show-progress -c -O "${SEDTHICK_DEST}.tmp" "$SEDTHICK_URL" && \
        mv "${SEDTHICK_DEST}.tmp" "$SEDTHICK_DEST"
    log "Download complete: $(du -h "$SEDTHICK_DEST" | cut -f1)"
fi

log "=== deck41/sediment download complete ==="
ls -lh "$BASE_DIR"/
