set dotenv-load

ssh_opts := "-o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
ssh_key := "-i terraform/benchmark-key.pem"

default:
    @just --list

# Provision instance, deploy scenario config, and launch background setup
init scenario:
    #!/usr/bin/env bash
    set -euo pipefail

    # Validate scenario
    just validate "{{scenario}}"

    # Parse region from scenario
    REGION=$(yq -r '.region' "{{scenario}}")

    # Terraform apply
    echo "==> Provisioning instance in $REGION..."
    terraform -chdir=terraform init -upgrade -input=false > /dev/null
    terraform -chdir=terraform apply -auto-approve -var "region=$REGION"

    IP=$(terraform -chdir=terraform output -raw public_ip)
    SSH="ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP"
    SCP="scp {{ssh_opts}} {{ssh_key}}"

    # Wait for SSH + cloud-init
    echo "==> Waiting for SSH on $IP..."
    until $SSH true 2>/dev/null; do sleep 2; done
    echo "==> Waiting for cloud-init..."
    $SSH 'cloud-init status --wait' > /dev/null 2>&1

    # Check if setup is already running or complete
    REMOTE_STATUS=$($SSH 'cat /data/setup/status 2>/dev/null || echo "none"')
    if [[ "$REMOTE_STATUS" == "ready" ]]; then
        echo "Setup already completed. Use 'just status' to check or 'just ssh' to connect."
        exit 0
    fi
    if [[ "$REMOTE_STATUS" =~ ^(starting|downloading|verifying|pulling)$ ]]; then
        echo "Setup already in progress (status: $REMOTE_STATUS). Use 'just status' to monitor."
        exit 0
    fi

    # Expand env vars in scenario YAML and deploy files
    echo "==> Deploying scenario config and scripts..."
    $SSH 'sudo mkdir -p /data/setup && sudo chown ubuntu:ubuntu /data/setup'
    envsubst < "{{scenario}}" | $SSH 'cat > /data/setup/scenario.yaml'
    $SCP scripts/setup.sh scripts/verify-blocks.sh ubuntu@$IP:/data/setup/
    $SSH 'chmod +x /data/setup/setup.sh /data/setup/verify-blocks.sh'

    # Launch setup as a supervised systemd unit
    echo "==> Launching background setup..."
    $SSH 'sudo systemd-run --unit=benchmark-setup --uid=ubuntu --gid=ubuntu \
        --property=StandardOutput=append:/data/setup/setup.log \
        --property=StandardError=append:/data/setup/setup.log \
        /data/setup/setup.sh'

    echo "==> Setup launched. Use 'just status' to monitor progress."

# Show setup status and recent log output
status:
    #!/usr/bin/env bash
    set -euo pipefail
    IP=$(terraform -chdir=terraform output -raw public_ip)
    SSH="ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP"
    echo "--- Status ---"
    $SSH 'cat /data/setup/status 2>/dev/null || echo "no status file"'
    echo ""
    echo "--- Last 20 log lines ---"
    $SSH 'tail -20 /data/setup/setup.log 2>/dev/null || echo "no log file"'

# SSH into the instance
ssh:
    #!/usr/bin/env bash
    set -euo pipefail
    IP=$(terraform -chdir=terraform output -raw public_ip)
    echo "Waiting for SSH on $IP..."
    until ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP true 2>/dev/null; do sleep 2; done
    ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP

# Validate a scenario file
validate scenario:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ ! -f "{{scenario}}" ]]; then
        echo "Error: scenario file '{{scenario}}' not found"
        exit 1
    fi
    ERRORS=()
    for field in name region image rpc_url; do
        val=$(yq -r ".$field // \"\"" "{{scenario}}")
        if [[ -z "$val" ]]; then
            ERRORS+=("missing required field: $field")
        fi
    done
    SNAPSHOT_URL=$(yq -r '.snapshot_url // ""' "{{scenario}}")
    SNAPSHOT_BUCKET=$(yq -r '.snapshot_bucket // ""' "{{scenario}}")
    if [[ -z "$SNAPSHOT_URL" && -z "$SNAPSHOT_BUCKET" ]]; then
        ERRORS+=("must set either snapshot_url or snapshot_bucket")
    fi
    if [[ -n "$SNAPSHOT_BUCKET" ]]; then
        for field in snapshot_key snapshot_region; do
            val=$(yq -r ".$field // \"\"" "{{scenario}}")
            if [[ -z "$val" ]]; then
                ERRORS+=("snapshot_bucket requires $field")
            fi
        done
    fi
    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        echo "Scenario validation failed:"
        for err in "${ERRORS[@]}"; do echo "  - $err"; done
        exit 1
    fi
    echo "Scenario '{{scenario}}' is valid."

# Destroy the instance
down:
    terraform -chdir=terraform destroy -auto-approve
