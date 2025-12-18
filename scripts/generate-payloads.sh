#!/bin/bash
set -euo pipefail

expb generate-payloads \
  --rpc-url "$ETH_RPC_URL" \
  --start-block 24029721 \
  --end-block 24029820 \
  --output-dir /data/expb
