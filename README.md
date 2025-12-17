# world-chain-benchmarking

world-chain-benchmarking repository
=======

# Ethereum Client Benchmarking

Terraform setup for provisioning EC2 instances for Ethereum client benchmarks.

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just) command runner
- AWS CLI configured with appropriate credentials

## Setup

1. Create your tfvars file:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

2. Edit `terraform/terraform.tfvars`:

```hcl
region           = "us-east-1"
instance_type    = "i4i.4xlarge"
root_volume_size = 500   # GB
```

3. Customize `terraform/user-data.sh` with your benchmark setup.

## Usage

Set your `AWS_PROFILE` env var.

```bash
just up      # Launch instance
just ssh     # SSH into instance
just logs    # Tail cloud-init logs
just down    # Destroy instance
```

Run `just` to see all available commands.

The SSH key pair is auto-generated and saved to `terraform/benchmark-key.pem`.

## Instance Details

- Ubuntu 22.04 LTS
- gp3 EBS volume with 16,000 IOPS / 1,000 MB/s throughput
- Ports open: 22 (SSH), 30303 (Ethereum P2P)
