# World Chain Benchmarking

Provisions a single EC2 instance with Rust and Docker pre-installed for Ethereum client benchmarking work.

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just)
- AWS credentials configured (`AWS_PROFILE`)

## Usage

```bash
just up      # Provision the instance
just ssh     # SSH into the instance
just status  # Show instance state and cloud-init status
just down    # Destroy the instance
```

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache 2.0](LICENSE-APACHE) at your option.
