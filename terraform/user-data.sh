#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y git curl build-essential neovim just zstd nvme-cli jq aria2

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
uv tool install --from git+https://github.com/NethermindEth/execution-payloads-benchmarks expb

# Clone the benchmarking repo
# git clone https://github.com/worldcoin/world-chain-benchmarking.git

echo "Ready"
USERSCRIPT
