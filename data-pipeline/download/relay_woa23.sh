#!/bin/bash
# Relay WOA23 files: x86-build-server → local pipe → ocean-server
# No local disk usage, uses SSH pipe
set -euo pipefail

SRC="x86-build-server"
DST="ocean-server"
SRC_DIR="/root/ocean_acoustic/woa23"
DST_DIR="/data/nas_data/ocean_acoustic/woa23"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

relay_file() {
    local subdir="$1"
    local filename="$2"
    local src_path="${SRC_DIR}/${subdir}/${filename}"
    local dst_path="${DST_DIR}/${subdir}/${filename}"

    # Check if already exists with correct size on destination
    local src_size
    src_size=$(ssh "$SRC" "stat -c%s '${src_path}'" 2>/dev/null)
    local dst_size
    dst_size=$(ssh "$DST" "stat -c%s '${dst_path}'" 2>/dev/null || echo "0")

    if [[ "$src_size" == "$dst_size" ]] && [[ "$dst_size" != "0" ]]; then
        log "SKIP (exists): ${subdir}/${filename}"
        return 0
    fi

    log "Transferring: ${subdir}/${filename} ($(numfmt --to=iec "$src_size"))"
    ssh "$SRC" "cat '${src_path}'" | ssh "$DST" "cat > '${dst_path}'"
    log "Done: ${subdir}/${filename}"
}

# Ensure directories exist
ssh "$DST" "mkdir -p ${DST_DIR}/temperature ${DST_DIR}/salinity"

# Transfer temperature files
log "=== Transferring Temperature Files ==="
for f in $(ssh "$SRC" "ls ${SRC_DIR}/temperature/*.nc" | xargs -n1 basename); do
    relay_file "temperature" "$f"
done

# Transfer salinity files
log "=== Transferring Salinity Files ==="
for f in $(ssh "$SRC" "ls ${SRC_DIR}/salinity/*.nc" | xargs -n1 basename); do
    relay_file "salinity" "$f"
done

log "=== All WOA23 transfers complete ==="
ssh "$DST" "du -sh ${DST_DIR}/temperature ${DST_DIR}/salinity"
