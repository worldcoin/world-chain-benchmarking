# Unwind snapshot
docker run -v /data/reth/reth:/data ghcr.io/paradigmxyz/op-reth:nightly stage unwind --chain worldchain --datadir /data to-block 24175000
docker run -v /data/reth/reth:/data ghcr.io/paradigmxyz/op-reth:nightly node --full --chain worldchain --datadir /data --http --http.addr=0.0.0.0 --http.api=admin,net,eth,web3,miner,debug,trace

# Run reth node for benchmarking
docker run -p 8545:8545 -p 8551:8551 -v /data/reth/reth:/data ghcr.io/paradigmxyz/op-reth:nightly node --full --chain worldchain --datadir /data --http --http.addr=0.0.0.0 --authrpc.addr=0.0.0.0 --http.api=admin,net,eth,web3,miner,debug,trace


BUCKET=jt-benchmarking-snapshots-0c836de28786b6f1
SIZE=$(du -sb "/data/reth/reth" | awk '{print $1}')
AWS_REGION=eu-central-2
S3_URL="s3://$BUCKET/reth_24175000.tar.zst"

tar -C "/data/reth" -cf - reth |
  lz4 -v -1 -c - |
  aws s3 cp - "$S3_URL.tmp" \
    --region "$AWS_REGION" \
    --expected-size "$SIZE"

tar -C "/data/reth" -cf - reth |
    zstd -T0 -1 -c - |
    mbuffer -m 512M |
    aws s3 cp - "$S3_URL.tmp" \
      --region "$AWS_REGION" \
      --expected-size "$SIZE"

tar -C "/data/reth" -cf - reth |
    zstd -T0 -1 -c - |
    pv |
    mbuffer -q -m 512M |
    aws s3 cp - "$S3_URL.tmp" \
      --region "$AWS_REGION" \
      --expected-size "$SIZE"

echo "[INFO] Finalising snapshot"
aws s3 cp "$S3_URL.tmp" "$S3_URL" --region "$AWS_REGION"
aws s3 rm "$S3_URL.tmp" --region "$AWS_REGION"

# Building reth-bench

# Make sure rust/cargo is installed
# Make sure clang is installed
git clone git@github.com:paradigmxyz/reth.git

# cd into it
make install-reth-bench

# Running the benchmark
reth-bench new-payload-fcu \
  --rpc-url "$WLD_RPC_URL" \
  --from 24175000 \
  --to 24176000 \
  --engine-rpc-url "http://localhost:8545" \
  --output ./benchmark_results/

./target/release/reth-bench new-payload-fcu --rpc-url "$WLD_RPC_URL" --from 24175000 --to 24218200--engine-rpc-url "http://localhost:8545" --output ./benchmark_results/
