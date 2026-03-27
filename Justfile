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

    # Parse region and optional instance_type from scenario
    REGION=$(yq -r '.region' "{{scenario}}")
    INSTANCE_TYPE=$(yq -r '.instance_type // ""' "{{scenario}}")

    # Terraform apply
    echo "==> Provisioning instance in $REGION..."
    terraform -chdir=terraform init -upgrade -input=false > /dev/null
    TF_VARS=(-var "region=$REGION")
    if [[ -n "$INSTANCE_TYPE" ]]; then
        TF_VARS+=(-var "instance_type=$INSTANCE_TYPE")
    fi
    terraform -chdir=terraform apply -auto-approve "${TF_VARS[@]}"

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

# Show instance state and setup progress
status:
    #!/usr/bin/env bash
    set -euo pipefail
    INSTANCE_ID=$(terraform -chdir=terraform output -raw instance_id)
    STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo "unknown")
    echo "--- Instance: $STATE ---"
    if [[ "$STATE" != "running" ]]; then
        echo "Instance is not running. Cannot check setup status."
        exit 0
    fi
    IP=$(terraform -chdir=terraform output -raw public_ip)
    SSH="ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP"
    echo "--- Setup Status ---"
    $SSH 'cat /data/setup/status 2>/dev/null || echo "not started"'
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
    if [[ -z "$SNAPSHOT_URL" ]]; then
        ERRORS+=("missing required field: snapshot_url")
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
