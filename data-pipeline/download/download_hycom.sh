#!/bin/bash
# Download HYCOM GOFS 3.1 global daily mean Temperature & Salinity
# Source: HYCOM Consortium THREDDS (GLBy0.08/expt_93.0)
# Resolution: 0.08° x 40 levels x daily
# Default: last 2 years of global daily data
#
# Usage:
#   ./download_hycom.sh                    # Download last 2 years
#   ./download_hycom.sh 2024 2025          # Download specific year range
#   ./download_hycom.sh 2025 2025 06 06    # Download specific month
#
# Requires: wget or curl
# Note: Each daily file is ~250-300 MB, ~200 GB total for 2 years

set -euo pipefail

BASE_DIR="/data/nas_data/ocean_acoustic/hycom"
# HYCOM GOFS 3.1 Analysis - GLBy0.08 experiment 93.0
# This provides 3-hourly data; we download 12:00Z snapshots as daily representative
THREDDS_BASE="https://tds.hycom.org/thredds/fileServer/GLBy0.08/expt_93.0"

mkdir -p "$BASE_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Parse arguments
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)
START_YEAR=${1:-$((CURRENT_YEAR - 2))}
END_YEAR=${2:-$CURRENT_YEAR}
START_MONTH=${3:-01}
END_MONTH=${4:-12}

TOTAL=0
DOWNLOADED=0
SKIPPED=0
FAILED=0

log "=== Downloading HYCOM GOFS 3.1 (GLBy0.08/expt_93.0) ==="
log "Period: ${START_YEAR}-${START_MONTH} to ${END_YEAR}-${END_MONTH}"
log "Destination: ${BASE_DIR}"

# Function to get days in month
days_in_month() {
    local year=$1 month=$2
    date -d "${year}-${month}-01 +1 month -1 day" +%d 2>/dev/null || \
        cal "$month" "$year" | awk 'NF {DAYS = $NF}; END {print DAYS}'
}

# Download a single HYCOM file
download_hycom_file() {
    local year="$1"
    local month="$2"
    local day="$3"
    local date_str="${year}${month}${day}"

    local year_dir="${BASE_DIR}/${year}"
    mkdir -p "$year_dir"

    # HYCOM file naming: ts3z/YYYYMMDD12_ts3z.nc (3D T/S at 12:00Z)
    # Alternative path format for newer data
    local filename="hycom_glby_930_${date_str}_t000_ts3z.nc"
    local dest="${year_dir}/${filename}"

    if [[ -f "$dest" ]]; then
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    # Try primary URL pattern (newer format)
    local url="${THREDDS_BASE}/ts3z/${date_str}12_ts3z.nc"

    if wget -q --timeout=120 --tries=3 -c -O "${dest}.tmp" "$url" 2>/dev/null; then
        mv "${dest}.tmp" "$dest"
        DOWNLOADED=$((DOWNLOADED + 1))
        return 0
    fi

    # Try alternative URL pattern
    url="${THREDDS_BASE}/ts3z/hycom_glby_930_${date_str}12_t000_ts3z.nc"
    if wget -q --timeout=120 --tries=3 -c -O "${dest}.tmp" "$url" 2>/dev/null; then
        mv "${dest}.tmp" "$dest"
        DOWNLOADED=$((DOWNLOADED + 1))
        return 0
    fi

    rm -f "${dest}.tmp"
    FAILED=$((FAILED + 1))
    log "FAILED: ${date_str}"
    return 1
}

# Main download loop
for year in $(seq "$START_YEAR" "$END_YEAR"); do
    # Determine month range for this year
    local_start_month=01
    local_end_month=12

    if [[ "$year" == "$START_YEAR" ]]; then
        local_start_month="$START_MONTH"
    fi
    if [[ "$year" == "$END_YEAR" ]]; then
        local_end_month="$END_MONTH"
        # Don't try future months
        if [[ "$year" == "$CURRENT_YEAR" ]] && [[ "$local_end_month" -gt "$CURRENT_MONTH" ]]; then
            local_end_month="$CURRENT_MONTH"
        fi
    fi

    for month in $(seq -w "$local_start_month" "$local_end_month"); do
        days=$(days_in_month "$year" "$month")
        log "Processing ${year}-${month} (${days} days)..."

        for day in $(seq -w 1 "$days"); do
            # Skip future dates
            today=$(date +%Y%m%d)
            if [[ "${year}${month}${day}" -gt "$today" ]]; then
                continue
            fi

            TOTAL=$((TOTAL + 1))
            download_hycom_file "$year" "$month" "$day" || true
        done

        # Monthly progress
        done_count=$((DOWNLOADED + SKIPPED + FAILED))
        log "Progress after ${year}-${month}: total=$done_count, downloaded=$DOWNLOADED, skipped=$SKIPPED, failed=$FAILED"
    done
done

log "=== HYCOM download complete ==="
log "Total processed: $((DOWNLOADED + SKIPPED + FAILED))"
log "Downloaded: $DOWNLOADED, Skipped: $SKIPPED, Failed: $FAILED"
du -sh "$BASE_DIR"
