#!/bin/bash
set -euo pipefail

RPC_URL="$1"
START_BLOCK="$2"
COUNT="${3:-10}"

echo "Verifying $COUNT blocks starting after block $START_BLOCK via $RPC_URL"

for i in $(seq 0 $((COUNT - 1))); do
    BLOCK_NUM=$((START_BLOCK + 1 + i))
    BLOCK_HEX=$(printf '0x%x' "$BLOCK_NUM")

    RESULT=$(curl -sf -X POST "$RPC_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"$BLOCK_HEX\",false],\"id\":1}")

    HASH=$(echo "$RESULT" | jq -r '.result.hash // empty')
    if [[ -z "$HASH" ]]; then
        echo "FAIL: block $BLOCK_NUM ($BLOCK_HEX) returned no hash"
        exit 1
    fi
    echo "OK: block $BLOCK_NUM hash=$HASH"
done

echo "All $COUNT blocks verified."
