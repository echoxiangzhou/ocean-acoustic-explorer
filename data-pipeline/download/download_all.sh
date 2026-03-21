#!/bin/bash
# Master download script for OceanAcoustic Explorer
# Downloads all required datasets to /data/nas_data/ocean_acoustic/
#
# Usage:
#   ./download_all.sh          # Download all datasets
#   ./download_all.sh woa23    # Download only WOA23
#   ./download_all.sh gebco    # Download only GEBCO
#   ./download_all.sh soda     # Download only SODA
#   ./download_all.sh deck41   # Download only deck41
#   ./download_all.sh hycom    # Download only HYCOM
#
# Run in background:
#   nohup ./download_all.sh > download.log 2>&1 &

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="/data/nas_data/ocean_acoustic"
LOG_FILE="${BASE_DIR}/download.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$BASE_DIR"

TARGET="${1:-all}"

log "========================================="
log "OceanAcoustic Explorer - Data Download"
log "Target: $TARGET"
log "Destination: $BASE_DIR"
log "========================================="

run_script() {
    local name="$1"
    local script="$2"
    shift 2

    log "--- Starting: $name ---"
    if bash "$script" "$@" 2>&1 | tee -a "$LOG_FILE"; then
        log "--- Completed: $name ---"
    else
        log "--- FAILED: $name ---"
        return 1
    fi
}

case "$TARGET" in
    woa23)
        run_script "WOA23" "${SCRIPT_DIR}/download_woa23.sh"
        ;;
    gebco)
        run_script "GEBCO" "${SCRIPT_DIR}/download_gebco.sh"
        ;;
    soda)
        run_script "SODA" "${SCRIPT_DIR}/download_soda.sh"
        ;;
    deck41)
        run_script "deck41" "${SCRIPT_DIR}/download_deck41.sh"
        ;;
    hycom)
        run_script "HYCOM" "${SCRIPT_DIR}/download_hycom.sh"
        ;;
    all)
        # Download in priority order (WOA23 and GEBCO needed first)
        run_script "WOA23"  "${SCRIPT_DIR}/download_woa23.sh"
        run_script "GEBCO"  "${SCRIPT_DIR}/download_gebco.sh"
        run_script "deck41" "${SCRIPT_DIR}/download_deck41.sh"
        run_script "HYCOM"  "${SCRIPT_DIR}/download_hycom.sh"
        run_script "SODA"   "${SCRIPT_DIR}/download_soda.sh"
        ;;
    *)
        echo "Usage: $0 [woa23|gebco|soda|deck41|hycom|all]"
        exit 1
        ;;
esac

log "========================================="
log "Download summary:"
du -sh "${BASE_DIR}"/*/ 2>/dev/null || true
log "Total: $(du -sh "$BASE_DIR" | cut -f1)"
log "========================================="
