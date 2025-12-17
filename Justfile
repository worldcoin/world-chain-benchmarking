set dotenv-load

ssh_opts := "-o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
ssh_key := "-i benchmark-key.pem"

default:
    @just --list

# Initialize Terraform
init:
    cd terraform && terraform init -upgrade

# Launch benchmark instance
up: init
    cd terraform && terraform apply -auto-approve

# Destroy benchmark instance
down:
    cd terraform && terraform destroy -auto-approve

# Stop instance (keeps data)
stop:
    #!/usr/bin/env bash
    set -euo pipefail
    cd terraform
    INSTANCE_ID=$(terraform output -raw instance_id)
    echo "Stopping instance $INSTANCE_ID..."
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
    aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"
    echo "Stopped."

# Start instance
start:
    #!/usr/bin/env bash
    set -euo pipefail
    cd terraform
    INSTANCE_ID=$(terraform output -raw instance_id)
    echo "Starting instance $INSTANCE_ID..."
    aws ec2 start-instances --instance-ids "$INSTANCE_ID"
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    terraform refresh
    echo "Running at $(terraform output -raw public_ip)"

# Show instance status
status:
    @cd terraform && aws ec2 describe-instance-status --instance-ids $(terraform output -raw instance_id) --query 'InstanceStatuses[0].InstanceState.Name' --output text 2>/dev/null || echo "stopped"

# Wait for instance to be ready
wait:
    #!/usr/bin/env bash
    set -euo pipefail
    cd terraform
    IP=$(terraform output -raw public_ip)
    echo "Waiting for SSH on $IP..."
    until ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP true 2>/dev/null; do
        sleep 2
    done
    echo "Waiting for cloud-init..."
    ssh {{ssh_opts}} {{ssh_key}} ubuntu@$IP 'cloud-init status --wait'
    echo "Ready!"

# SSH into the instance (waits for ready)
ssh: wait
    @cd terraform && ssh {{ssh_opts}} {{ssh_key}} ubuntu@$(terraform output -raw public_ip)

# SSH without waiting
ssh-now:
    @cd terraform && ssh {{ssh_opts}} {{ssh_key}} ubuntu@$(terraform output -raw public_ip)

# Show instance IP
ip:
    @cd terraform && terraform output -raw public_ip

# Tail cloud-init logs on the instance
logs:
    @cd terraform && ssh {{ssh_opts}} {{ssh_key}} ubuntu@$(terraform output -raw public_ip) 'tail -f /var/log/cloud-init-output.log'

# Show Terraform outputs
output:
    cd terraform && terraform output

# Format Terraform files
fmt:
    cd terraform && terraform fmt
