"""Utility functions for benchmarking CLI."""

import os
import secrets
import subprocess
import time
from datetime import datetime

from rich.console import Console

console = Console()


def generate_run_id() -> str:
    """Generate a unique run ID (timestamp + random hex)."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_hex = secrets.token_hex(4)
    return f"{timestamp}-{random_hex}"


def run(
    cmd: list[str] | str,
    *,
    check: bool = True,
    capture: bool = False,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    sudo: bool = False,
    retries: int = 0,
    retry_delay: float = 5.0,
) -> subprocess.CompletedProcess:
    """Run a subprocess with logging, error handling, and optional retry.

    Args:
        cmd: Command to run (list or string)
        check: Raise exception on non-zero exit code
        capture: Capture stdout/stderr
        cwd: Working directory
        env: Environment variables (merged with current env)
        sudo: Prepend sudo to command
        retries: Number of retries on failure
        retry_delay: Seconds to wait between retries
    """
    if isinstance(cmd, str):
        cmd = cmd.split()

    if sudo:
        cmd = ["sudo"] + cmd

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    cmd_str = " ".join(cmd)
    console.print(f"[dim]$ {cmd_str}[/dim]")

    attempt = 0
    last_error = None

    while attempt <= retries:
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture,
                text=True,
                cwd=cwd,
                env=full_env,
            )
            return result
        except subprocess.CalledProcessError as e:
            last_error = e
            if attempt < retries:
                attempt += 1
                console.print(f"[yellow]Command failed, retrying ({attempt}/{retries})...[/yellow]")
                time.sleep(retry_delay)
            else:
                raise

    raise last_error  # type: ignore


def run_docker(
    image: str,
    cmd: list[str],
    *,
    volumes: dict[str, str] | None = None,
    ports: dict[int, int] | None = None,
    env: dict[str, str] | None = None,
    detach: bool = False,
    remove: bool = True,
    name: str | None = None,
) -> subprocess.CompletedProcess | str:
    """Run a Docker container.

    Args:
        image: Docker image to run
        cmd: Command to run in container
        volumes: Host:container volume mappings
        ports: Host:container port mappings
        env: Environment variables
        detach: Run in background (returns container ID)
        remove: Remove container after exit (ignored if detach=True)
        name: Container name

    Returns:
        CompletedProcess if detach=False, container ID string if detach=True
    """
    docker_cmd = ["docker", "run"]

    if detach:
        docker_cmd.append("-d")
    elif remove:
        docker_cmd.append("--rm")

    if name:
        docker_cmd.extend(["--name", name])

    if volumes:
        for host_path, container_path in volumes.items():
            docker_cmd.extend(["-v", f"{host_path}:{container_path}"])

    if ports:
        for host_port, container_port in ports.items():
            docker_cmd.extend(["-p", f"{host_port}:{container_port}"])

    if env:
        for key, value in env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

    docker_cmd.append(image)
    docker_cmd.extend(cmd)

    result = run(docker_cmd, capture=detach)

    if detach:
        return result.stdout.strip()
    return result


def docker_stop(container: str, timeout: int = 10) -> None:
    """Stop a running Docker container."""
    run(["docker", "stop", "-t", str(timeout), container], check=False)


def docker_rm(container: str) -> None:
    """Remove a Docker container."""
    run(["docker", "rm", "-f", container], check=False)


def clear_caches() -> None:
    """Clear system caches (requires sudo)."""
    console.print("[dim]Clearing system caches...[/dim]")
    run(["sync"])
    run(["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], sudo=True)
