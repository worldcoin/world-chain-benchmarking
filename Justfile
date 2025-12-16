set dotenv-load

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

# SSH into the instance
ssh:
    @cd terraform && eval $(terraform output -raw ssh)

# Show instance IP
ip:
    @cd terraform && terraform output -raw public_ip

# Tail cloud-init logs on the instance
logs:
    @cd terraform && ssh -i benchmark-key.pem ubuntu@$(terraform output -raw public_ip) 'tail -f /var/log/cloud-init-output.log'

# Show Terraform outputs
output:
    cd terraform && terraform output

# Format Terraform files
fmt:
    cd terraform && terraform fmt
