# World Chain Benchmarking

Provisions a single EC2 instance with Rust and Docker pre-installed for Ethereum client benchmarking work.

## Prerequisites

- [Terraform](https://terraform.io) >= 1.0
- [Just](https://github.com/casey/just)
- AWS credentials configured (`AWS_PROFILE`)

### Required AWS permissions

`just up` calls `ec2:RunInstances` directly from your local session. The TFH org-wide `PowerUserAccess` and `BREAKGlassPowerUserAccess` SSO permission sets explicitly **deny** `ec2:RunInstances` (Linear `INFRA-2677`), so an SSO session using either of those will fail at apply time.

Use an SSO profile bound to `AdministratorAccess` on the target account (e.g. `worldcoin-crypto-dev`). Minimum permissions actually needed by `terraform/`: `ec2:RunInstances`, `ec2:Describe*`, `ec2:CreateSecurityGroup` / `AuthorizeSecurityGroup*` / `DeleteSecurityGroup`, `ec2:ImportKeyPair` / `DeleteKeyPair`, `ec2:TerminateInstances`, plus `ec2:CreateTags` and the matching `Delete` actions for teardown.

## Usage

```bash
just up                 # Provision the instance
just snapshot <url>     # Download a chain snapshot (s3:// or https://) to /data/snapshot
just ssh                # SSH into the instance
just status             # Show instance state and cloud-init status
just down               # Destroy the instance
```

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache 2.0](LICENSE-APACHE) at your option.
