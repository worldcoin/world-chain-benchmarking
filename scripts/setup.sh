#!/bin/bash
set -euo pipefail

STATUS_DIR="/data/setup"
STATUS_FILE="$STATUS_DIR/status"
LOG_FILE="$STATUS_DIR/setup.log"
CONFIG="$STATUS_DIR/scenario.yaml"

write_status() {
    echo "$1" > "$STATUS_FILE"
    echo "[$(date -Iseconds)] $1" >> "$LOG_FILE"
}

trap 'write_status "failed: ${BASH_COMMAND} (line ${LINENO})"' ERR

mkdir -p "$STATUS_DIR"
write_status "starting"

# Parse scenario config
NAME=$(yq -r '.name' "$CONFIG")
IMAGE=$(yq -r '.image' "$CONFIG")
RPC_URL=$(yq -r '.rpc_url' "$CONFIG")

SNAPSHOT_DIR="/data/snapshots/$NAME"

# --- Download snapshot ---
write_status "downloading"
mkdir -p "$SNAPSHOT_DIR"

SNAPSHOT_URL=$(yq -r '.snapshot_url // ""' "$CONFIG")

# Detect decompression command from URL extension
decompress_cmd() {
    case "$1" in
        *.tar.lz4|*.lz4) echo "lz4 -d" ;;
        *.tar.zst|*.tar.zstd|*.zst|*.zstd) echo "zstd -d" ;;
        *) echo "zstd -d" ;;
    esac
}

DECOMPRESS=$(decompress_cmd "$SNAPSHOT_URL")

if [[ "$SNAPSHOT_URL" == s3://* ]]; then
    timeout 7200 s5cmd --no-sign-request cat "$SNAPSHOT_URL" | $DECOMPRESS | tar x -C "$SNAPSHOT_DIR"
elif [[ "$SNAPSHOT_URL" == https://* ]] || [[ "$SNAPSHOT_URL" == http://* ]]; then
    TMPFILE="$STATUS_DIR/snapshot-download.tmp"
    aria2c -x 16 -s 16 --file-allocation=none -d "$STATUS_DIR" -o "snapshot-download.tmp" "$SNAPSHOT_URL"
    $DECOMPRESS "$TMPFILE" | tar x -C "$SNAPSHOT_DIR"
    rm -f "$TMPFILE"
else
    write_status "failed: no valid snapshot_url specified"
    exit 1
fi

# --- Verify blocks (optional, requires snapshot_block) ---
SNAPSHOT_BLOCK=$(yq -r '.snapshot_block // ""' "$CONFIG")
if [[ -n "$SNAPSHOT_BLOCK" ]]; then
    write_status "verifying"
    /data/setup/verify-blocks.sh "$RPC_URL" "$SNAPSHOT_BLOCK"
fi

# --- Pull docker image ---
write_status "pulling"
docker pull "$IMAGE"

write_status "ready"
