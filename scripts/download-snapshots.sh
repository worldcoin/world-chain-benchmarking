#!/bin/bash
set -euo pipefail

NETWORK="mainnet"
BLOCK_NUMBER=24029720
OUTPUT_DIR="${1:-.}"
CONNECTIONS=16

download_snapshot() {
  local client="$1"
  local outdir="$OUTPUT_DIR/$client"
  local url="https://snapshots.ethpandaops.io/$NETWORK/$client/$BLOCK_NUMBER/snapshot.tar.zst"
  local archive="$OUTPUT_DIR/$client.tar.zst"

  mkdir -p "$outdir"

  echo "[$client] Downloading snapshot for block $BLOCK_NUMBER..."
  aria2c -x "$CONNECTIONS" -s "$CONNECTIONS" -k 100M \
    --file-allocation=none \
    -d "$OUTPUT_DIR" -o "$client.tar.zst" \
    "$url"

  echo "[$client] Extracting..."
  tar -I zstd -xf "$archive" -C "$outdir"
  rm "$archive"

  echo "[$client] Done!"
}

echo "Downloading snapshots to $OUTPUT_DIR (using $CONNECTIONS connections per download)"

download_snapshot "geth" &
# download_snapshot "reth" &
# download_snapshot "nethermind" &

wait
echo "All downloads complete!"
