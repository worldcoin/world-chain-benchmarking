#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y git curl build-essential neovim zstd lz4 nvme-cli jq aria2 clang

# Install just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# install s3fcp
curl -L "https://github.com/Dzejkop/s3fcp/releases/download/v0.2.1/s3fcp-linux-x86_64" -o "/usr/local/bin/s3fcp" &&
  chmod +x /usr/local/bin/s3fcp

# Mount instance store NVMe SSD at /data
NVME_DEVICE=$(nvme list -o json | jq -r '.Devices[] | select(.ModelNumber | contains("Instance Storage")) | .DevicePath' | head -1)
if [ -n "$NVME_DEVICE" ]; then
  mkfs.ext4 -F "$NVME_DEVICE"
  mkdir -p /data
  mount "$NVME_DEVICE" /data
  chown ubuntu:ubuntu /data
  echo "$NVME_DEVICE /data ext4 defaults,nofail 0 2" >>/etc/fstab
  echo "Mounted instance store at /data"
fi

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Run remaining setup as ubuntu user
sudo -u ubuntu bash <<'USERSCRIPT'
set -euo pipefail
cd ~

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

# Install Rust (for reth-bench)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Clone and build reth-bench
git clone https://github.com/paradigmxyz/reth.git
cd reth
make install-reth-bench
cd ~

# Clone the benchmarking repo
git clone https://github.com/worldcoin/world-chain-benchmarking.git benchmarking
cd benchmarking
uv sync

echo "Ready"
USERSCRIPT
