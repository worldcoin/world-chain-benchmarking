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
SNAPSHOT_URL=$(yq -r '.snapshot_url' "$CONFIG")
SNAPSHOT_BLOCK=$(yq -r '.snapshot_block' "$CONFIG")
RPC_URL=$(yq -r '.rpc_url' "$CONFIG")

SNAPSHOT_DIR="/data/snapshots/$NAME"

# --- Download snapshot ---
write_status "downloading"
mkdir -p "$SNAPSHOT_DIR"

if [[ "$SNAPSHOT_URL" == s3://* ]]; then
    timeout 7200 s5cmd --no-sign-request cat "$SNAPSHOT_URL" | zstd -d | tar x -C "$SNAPSHOT_DIR"
elif [[ "$SNAPSHOT_URL" == https://* ]] || [[ "$SNAPSHOT_URL" == http://* ]]; then
    curl -fL --speed-limit 1048576 --speed-time 60 "$SNAPSHOT_URL" | zstd -d | tar x -C "$SNAPSHOT_DIR"
else
    write_status "failed: unsupported URL scheme: $SNAPSHOT_URL"
    exit 1
fi

# --- Verify blocks ---
write_status "verifying"
/data/setup/verify-blocks.sh "$RPC_URL" "$SNAPSHOT_BLOCK"

# --- Pull docker image ---
write_status "pulling"
docker pull "$IMAGE"

write_status "ready"
