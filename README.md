# World Chain Benchmarking

Provisions EC2 instances for Ethereum client benchmarks. A single `just init` command spins up an instance, downloads a chain snapshot, verifies block availability, and pulls the docker image.

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just)
- [yq](https://github.com/mikefarah/yq)
- AWS credentials configured (`AWS_PROFILE`)

## Usage

```bash
just init scenarios/worldchain-sepolia.yaml   # Provision + setup
just status                                    # Check setup progress
just ssh                                       # SSH into instance
just down                                      # Destroy instance
just validate scenarios/worldchain-sepolia.yaml # Validate scenario file
```

## Scenarios

Scenario YAML files in `scenarios/` define what to benchmark. See `scenarios/worldchain-sepolia.yaml` for an example.

Required fields: `name`, `region`, `image`, `rpc_url`, and either `snapshot_url` or `snapshot_bucket` (with `snapshot_key`, `snapshot_region`).

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache 2.0](LICENSE-APACHE) at your option.
