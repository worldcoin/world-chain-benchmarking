#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y git curl build-essential

# Add your benchmark setup here
echo "Here's where benchmark results will be!"
