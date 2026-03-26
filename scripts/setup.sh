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
SNAPSHOT_BUCKET=$(yq -r '.snapshot_bucket // ""' "$CONFIG")

if [[ -n "$SNAPSHOT_BUCKET" ]]; then
    # S3 versioned bucket download (World Chain snapshots)
    SNAPSHOT_KEY=$(yq -r '.snapshot_key' "$CONFIG")
    SNAPSHOT_REGION=$(yq -r '.snapshot_region' "$CONFIG")
    VID=$(aws s3api head-object --bucket "$SNAPSHOT_BUCKET" --key "$SNAPSHOT_KEY" \
        --region "$SNAPSHOT_REGION" --query 'VersionId' --output text)
    aws s3api get-object --bucket "$SNAPSHOT_BUCKET" --key "$SNAPSHOT_KEY" \
        --version-id "$VID" --region "$SNAPSHOT_REGION" --no-cli-pager /dev/stdout \
        | lz4 -d | tar x -C "$SNAPSHOT_DIR"
elif [[ "$SNAPSHOT_URL" == s3://* ]]; then
    timeout 7200 s5cmd --no-sign-request cat "$SNAPSHOT_URL" | zstd -d | tar x -C "$SNAPSHOT_DIR"
elif [[ "$SNAPSHOT_URL" == https://* ]] || [[ "$SNAPSHOT_URL" == http://* ]]; then
    curl -fL --speed-limit 1048576 --speed-time 60 "$SNAPSHOT_URL" | zstd -d | tar x -C "$SNAPSHOT_DIR"
else
    write_status "failed: no snapshot_url or snapshot_bucket specified"
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
