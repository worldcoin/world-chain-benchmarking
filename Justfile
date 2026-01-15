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

# Terraform/EC2 commands (delegate to terraform/Justfile)
up:
    @just --justfile terraform/Justfile up

down:
    @just --justfile terraform/Justfile down

ssh:
    @just --justfile terraform/Justfile ssh

download-results:
    @just --justfile terraform/Justfile download-results

tf *args:
    @just --justfile terraform/Justfile {{args}}
