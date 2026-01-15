# world-chain-benchmarking

Benchmarking setup for Ethereum execution clients using [reth-bench](https://github.com/paradigmxyz/reth/tree/main/bin/reth-bench).

## Supported Clients

| Client | Networks |
|--------|----------|
| reth | ethereum-mainnet |
| op-reth | worldchain-mainnet |
| nethermind | ethereum-mainnet, worldchain-mainnet |
| geth | ethereum-mainnet |
| op-geth | worldchain-mainnet |

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just) command runner
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- AWS CLI configured with appropriate credentials

## Setup

1. Create your tfvars file:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

2. Edit `terraform/terraform.tfvars`:

```hcl
region           = "eu-central-2"
instance_type    = "i4i.4xlarge"
root_volume_size = 50
```

3. Create `.env` with RPC URLs (required for benchmarking):

```bash
ETH_RPC_URL=https://your-ethereum-rpc-url.com
WLD_RPC_URL=https://your-worldchain-rpc-url.com
```

## Quick Start

```bash
# 1. Launch EC2 instance
just up

# 2. SSH into instance (waits for cloud-init to complete)
just ssh

# 3. On the instance: download snapshot
just snapshot reth ethereum-mainnet --block 23900000

# 4. On the instance: run benchmark
just run reth ethereum-mainnet --from 23900000 --to 23900100

# 5. On the instance: upload results (optional)
just upload --bucket your-s3-bucket

# 6. Destroy instance when done
just down
```

## Commands

### Infrastructure (run locally)

| Command | Description |
|---------|-------------|
| `just up` | Launch benchmark EC2 instance |
| `just down` | Destroy instance |
| `just ssh` | SSH in (waits for cloud-init, loads .env) |
| `just tf status` | Show instance state |
| `just tf logs` | Tail cloud-init logs |
| `just tf ip` | Show instance public IP |

### Benchmarking (run on EC2 instance)

| Command | Description |
|---------|-------------|
| `just snapshot <client> <network> --block <n>` | Download snapshot |
| `just run <client> <network> --from <n> --to <n>` | Run benchmark |
| `just upload --bucket <bucket>` | Upload results to S3 |
| `just profile <client> --from <n> --to <n>` | Run with profiling (reth/op-reth only) |

### Benchmark Options

```bash
# Run with specific client version
just run reth ethereum-mainnet --from 23900000 --to 23900100 --version v1.2.0

# Run multiple iterations
just run reth ethereum-mainnet --from 23900000 --to 23900100 --runs 5

# Use different data directory
just run reth ethereum-mainnet --from 23900000 --to 23900100 --data-dir /mnt/data
```

## How It Works

1. **Snapshot download**: Fetches a pre-synced database snapshot from S3/ethPandaOps
2. **Unwind**: Rolls back the snapshot to the target start block (reth/op-reth only)
3. **Benchmark**: Starts the execution client in Docker, runs `reth-bench new-payload-fcu` which:
   - Fetches block payloads from an archive RPC
   - Sends `engine_newPayload` + `engine_forkchoiceUpdated` to the client
   - Measures execution time per block
4. **Results**: Saves JSON output to `/data/results/`

## Instance Details

- Ubuntu 22.04 LTS
- i4i.4xlarge: 16 vCPUs, 128 GB RAM, 1 x 3,750 GB NVMe SSD mounted at `/data`
- Pre-installed: Docker, Rust, reth-bench, uv, Python

## Results Format

Results are saved to `/data/results/<run-id>/`:

```
/data/results/20260108-103308-abc123/
  metadata.json       # Run configuration
  bench_<from>_<to>.json  # reth-bench output per run
```

## License

Unless otherwise specified, all code in this repository is dual-licensed under
either:

- MIT License ([LICENSE-MIT](LICENSE-MIT))
- Apache License, Version 2.0, with LLVM Exceptions
  ([LICENSE-APACHE](LICENSE-APACHE))

at your option. This means you may select the license you prefer to use.
