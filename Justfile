set dotenv-load

default:
    @just --list

# Run benchmark
run *args:
    uv run bench run {{args}}

# Download snapshot
snapshot *args:
    uv run bench snapshot {{args}}

# Upload results to S3
upload *args:
    uv run bench upload {{args}}

# Run profiled benchmark
profile *args:
    uv run bench profile {{args}}

# Terraform commands
tf *args:
    cd terraform && terraform {{args}}

# Provision EC2 instance
up:
    just tf apply -auto-approve

# Destroy EC2 instance
down:
    just tf destroy -auto-approve

# SSH into EC2 instance
ssh:
    @just --justfile terraform/Justfile ssh
