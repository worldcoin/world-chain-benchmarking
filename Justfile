set dotenv-load

default:
    @just --list

# Terraform commands (just tf <cmd>)
tf cmd="":
    @just --justfile terraform/Justfile {{cmd}}

# Start monitoring stack (Prometheus, Grafana, Pyroscope)
monitoring-up:
    docker compose up -d

# Stop monitoring stack
monitoring-down:
    docker compose down

# Show monitoring logs
monitoring-logs:
    docker compose logs -f

# Restart monitoring stack
monitoring-restart:
    docker compose restart
