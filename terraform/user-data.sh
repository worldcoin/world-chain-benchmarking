#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y git curl build-essential neovim zstd nvme-cli jq aria2

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

# Install Nethermind's benchmark tool
# uv tool install --from git+https://github.com/NethermindEth/execution-payloads-benchmarks expb
uv tool install --from git+https://github.com/dzejkop/execution-payloads-benchmarks expb

# Clone the benchmarking repo
git clone https://github.com/worldcoin/world-chain-benchmarking.git

echo "Ready"
USERSCRIPT
