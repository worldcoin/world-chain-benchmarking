set dotenv-load

default:
    @just --list

# Terraform commands (just tf <cmd>)
tf cmd="":
    @just --justfile terraform/Justfile {{cmd}}
