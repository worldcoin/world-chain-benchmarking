#!/bin/bash
set -euo pipefail

NETWORK="mainnet"
BLOCK_NUMBER="${BLOCK_NUMBER:-24029720}"
CONNECTIONS="${CONNECTIONS:-16}"

usage() {
  echo "Usage: $0 <client> [output_dir]"
  echo "  client: geth, reth, or nethermind"
  echo "  output_dir: defaults to current directory"
  echo ""
  echo "Environment variables:"
  echo "  BLOCK_NUMBER  - snapshot block (default: $BLOCK_NUMBER)"
  echo "  CONNECTIONS   - parallel connections (default: $CONNECTIONS)"
  exit 1
}

[[ $# -lt 1 ]] && usage

CLIENT="$1"
OUTPUT_DIR="${2:-.}"
OUTDIR="$OUTPUT_DIR/$CLIENT"
URL="https://snapshots.ethpandaops.io/$NETWORK/$CLIENT/$BLOCK_NUMBER/snapshot.tar.zst"
ARCHIVE="$OUTPUT_DIR/$CLIENT.tar.zst"

mkdir -p "$OUTDIR"

echo "[$CLIENT] Downloading snapshot for block $BLOCK_NUMBER..."
aria2c -x "$CONNECTIONS" -s "$CONNECTIONS" -k 100M \
  --file-allocation=none \
  -d "$OUTPUT_DIR" -o "$CLIENT.tar.zst" \
  "$URL"

echo "[$CLIENT] Extracting..."
tar -I zstd -xf "$ARCHIVE" -C "$OUTDIR"
rm "$ARCHIVE"

echo "[$CLIENT] Done!"
