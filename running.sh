# Nethermind benchmark
just snapshot nethermind ethereum-mainnet --block 22830000
just run nethermind ethereum-mainnet --from 22830000 --to 22830100

# Geth benchmark
just snapshot geth ethereum-mainnet --block 22830000
just run geth ethereum-mainnet --from 22830000 --to 22830100

# Reth benchmark
just snapshot reth ethereum-mainnet --block 22830000
just run reth ethereum-mainnet --from 22829999 --to 22830100
just run reth ethereum-mainnet --from 22830000 --to 22830100

reth-bench new-payload-fcu \
  --rpc-url $ETH_RPC_URL \
  --from 22829998 --to 22830100 \
  --engine-rpc-url http://localhost:8551 \
  --jwt-secret /data/runs/manual/jwt.hex \
  --output /data/results/manual \
  --full-requests \
  --beacon-api-url $BEACON_API_URL

docker run --rm -v /data/runs/manual:/data \
  ghcr.io/paradigmxyz/reth:latest \
  stage unwind --datadir /data to-block 22830000 --chain mainnet
