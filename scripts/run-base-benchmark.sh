#!/bin/bash
set -euo pipefail

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install client deps
sudo apt-get install -y build-essential clang pkg-config libssl-dev

# Install mise
curl https://mise.run | sh

# Auto activate mise
echo 'eval "$(~/.local/bin/mise activate bash)"' >>~/.bashrc

# Misen eeds to be activated
eval "$(mise activate bash)"

# Go to home dir
cd "$HOME" || exit

# Clone base benchmark repo
git clone https://github.com/base/benchmark.git
cd benchmark || exit

# Init repo
git submodule update --init --recursive

# Install deps
mise trust
mise install

# Build
make build
make build-binaries

# First benchmark
./bin/base-bench run \
  --config ./configs/public/basic.yml \
  --reth-bin clients/build/reth/target/maxperf/op-reth \
  --root-dir ./data-dir \
  --output-dir ./output

cd report/ || exit
npm install
npm run dev
