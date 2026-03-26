#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y git curl build-essential neovim zstd nvme-cli jq

# Install just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

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

# Install s5cmd
curl -sL https://github.com/peak/s5cmd/releases/download/v2.3.0/s5cmd_2.3.0_linux_amd64.tar.gz | tar xz -C /tmp
mv /tmp/s5cmd /usr/local/bin/

# Install yq
curl -sL https://github.com/mikefarah/yq/releases/download/v4.44.1/yq_linux_amd64 -o /usr/local/bin/yq
chmod +x /usr/local/bin/yq

echo "Ready"
