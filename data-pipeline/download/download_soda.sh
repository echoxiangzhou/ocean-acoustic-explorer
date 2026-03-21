#!/bin/bash
# Download SODA 3.15.2 5-day ocean reanalysis (1980-2019)
# Source: University of Maryland (dsrs.atmos.umd.edu)
# Format: soda3.15.2_5dy_ocean_reg_YYYY_MM_DD.nc (~286MB each)
# Variables: temp(50lev), salt(50lev), u, v, w, prho, ssh, mlt, etc. (21 vars)
# Grid: 0.5° x 0.5°, 720x330, 50 z-levels (5m-5395m)
# Total: ~2920 files (73/year * 40 years), ~820 GB
#
# Usage:
#   ./download_soda.sh              # Download 1980-2019
#   ./download_soda.sh 2010 2019    # Download specific year range

set -euo pipefail

BASE_DIR="/data/nas_data/ocean_acoustic/soda"
BASE_URL="https://dsrs.atmos.umd.edu/DATA/soda3.15.2/REGRIDED/ocean"

mkdir -p "$BASE_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

START_YEAR=${1:-1980}
END_YEAR=${2:-2019}

DOWNLOADED=0
SKIPPED=0
FAILED=0

log "=== Downloading SODA 3.15.2 5-day ($START_YEAR-$END_YEAR) ==="

# SODA 3.15.2 uses 5-day intervals: Jan 3, Jan 8, Jan 13, ...
# Generate dates for each year
for year in $(seq "$START_YEAR" "$END_YEAR"); do
    year_dir="${BASE_DIR}/${year}"
    mkdir -p "$year_dir"

    # Start from Jan 3 each year, increment by 5 days
    # Use date arithmetic to generate all 5-day dates
    current="${year}-01-03"
    end_date="$((year + 1))-01-01"

    while [[ "$current" < "$end_date" ]]; do
        # Format: YYYY_MM_DD
        y=$(echo "$current" | cut -d- -f1)
        m=$(echo "$current" | cut -d- -f2)
        d=$(echo "$current" | cut -d- -f3)

        filename="soda3.15.2_5dy_ocean_reg_${y}_${m}_${d}.nc"
        dest="${year_dir}/${filename}"

        if [[ -f "$dest" ]]; then
            size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo "0")
            if [[ "$size" -gt 100000000 ]]; then
                SKIPPED=$((SKIPPED + 1))
                current=$(date -d "$current + 5 days" +%Y-%m-%d 2>/dev/null || \
                          date -j -v+5d -f "%Y-%m-%d" "$current" +%Y-%m-%d 2>/dev/null)
                continue
            fi
        fi

        url="${BASE_URL}/${filename}"
        if wget -q --show-progress --timeout=120 --tries=3 -c -O "${dest}.tmp" "$url" 2>/dev/null; then
            mv "${dest}.tmp" "$dest"
            DOWNLOADED=$((DOWNLOADED + 1))
        else
            rm -f "${dest}.tmp"
            FAILED=$((FAILED + 1))
        fi

        # Progress every 20 files
        total=$((DOWNLOADED + SKIPPED + FAILED))
        if (( total % 20 == 0 )); then
            log "Progress $year: downloaded=$DOWNLOADED, skipped=$SKIPPED, failed=$FAILED"
        fi

        # Next 5-day step
        current=$(date -d "$current + 5 days" +%Y-%m-%d 2>/dev/null || \
                  date -j -v+5d -f "%Y-%m-%d" "$current" +%Y-%m-%d 2>/dev/null)
    done

    log "Year $year done: downloaded=$DOWNLOADED, skipped=$SKIPPED, failed=$FAILED"
done

log "=== SODA download complete ==="
log "Downloaded: $DOWNLOADED, Skipped: $SKIPPED, Failed: $FAILED"
du -sh "$BASE_DIR"
