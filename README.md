# world-chain-benchmarking

Terraform setup for provisioning EC2 instances for Ethereum client benchmarks.

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just) command runner
- AWS CLI configured with appropriate credentials
- Docker (for monitoring stack)

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

3. (Optional) Create `.env` for secrets passed to the instance:

```bash
RPC_URL=https://your-rpc-url.com
```

## Commands

### Infrastructure (`just tf <cmd>`)

You should run these on your own machine.

| Command | Description |
|---------|-------------|
| `just tf up` | Launch benchmark instance |
| `just tf down` | Destroy instance |
| `just tf status` | Show instance state |
| `just tf ssh` | SSH in (waits for cloud-init, loads .env) |
| `just tf ssh-now` | SSH in immediately |
| `just tf logs` | Tail cloud-init logs |
| `just tf ip` | Show instance public IP |
| `just tf output` | Show all Terraform outputs |

### Monitoring Stack

These should be run in the EC2 instance.

| Command | Description |
|---------|-------------|
| `just monitoring-up` | Start Prometheus, Grafana, Pyroscope |
| `just monitoring-down` | Stop monitoring stack |
| `just monitoring-logs` | Tail monitoring logs |
| `just monitoring-restart` | Restart monitoring stack |

## SSH Features

- Auto-loads `.env` from repo root and exports vars to remote session
- Port forwards: Grafana (3000), Prometheus (9090), Pyroscope (4040)
- Auto-cd into `~/world-chain-benchmarking` on remote

## Instance Details

- Ubuntu 22.04 LTS
- i4i.4xlarge: 1 x 3,750 GB NVMe SSD mounted at `/data`
- gp3 EBS root volume (50GB)
- Ports open: 22 (SSH), 30303 (Ethereum P2P)
- SSH key auto-generated at `terraform/benchmark-key.pem`

## License

Unless otherwise specified, all code in this repository is dual-licensed under
either:

- MIT License ([LICENSE-MIT](LICENSE-MIT))
- Apache License, Version 2.0, with LLVM Exceptions
  ([LICENSE-APACHE](LICENSE-APACHE))

at your option. This means you may select the license you prefer to use.

Any contribution intentionally submitted for inclusion in the work by you, as
defined in the Apache-2.0 license, shall be dual licensed as above, without any
additional terms or conditions.
