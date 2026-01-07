#!/bin/bash
set -euo pipefail

NETWORK="mainnet"
BLOCK_NUMBER="${BLOCK_NUMBER:-23910000}"
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

mkdir -p "$OUTDIR"

echo "[$CLIENT] Downloading snapshot for block $BLOCK_NUMBER..."
s3fcp http -c "$CONNECTIONS" --chunk-size 100MB "$URL" | tar -I zstd -C "/$OUTPUT_DIR/$CLIENT" -x
s3fcp s3 "s3://world-chain-snapshots/reth_full.tar.lz4" | tar -I lz4 -C "/data/reth" -x

echo "[$CLIENT] Done!"
