#!/bin/bash
set -euo pipefail

# We need sudo because the tool cleans system cashe before running
sudo /home/ubuntu/.local/bin/expb execute-scenario --config-file expb.yaml --scenario-name example-nethermind

echo "Done!"
