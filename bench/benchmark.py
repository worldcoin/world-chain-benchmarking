"""Benchmark execution using reth-bench."""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from .clients import (
    get_client,
    get_docker_image,
    get_node_cmd,
    get_unwind_cmd,
    validate_client_network,
)
from .snapshots import get_rpc_url, get_snapshot_path
from .utils import (
    clear_caches,
    docker_stop,
    docker_rm,
    generate_run_id,
    run,
    run_docker,
)

console = Console()

# Default ports
HTTP_PORT = 8545
ENGINE_PORT = 8551


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    client: str
    network: str
    version: str
    from_block: int
    to_block: int
    runs: int
    data_dir: str


@dataclass
class RunResult:
    """Result of a single benchmark run."""

    run_number: int
    output_file: Path
    duration_seconds: float


def unwind_to_block(
    client_name: str,
    network: str,
    block: int,
    data_dir: str,
    version: str = "latest",
) -> None:
    """Unwind a client to a specific block."""
    unwind_cmd = get_unwind_cmd(client_name, network, block, datadir="/data")

    if unwind_cmd is None:
        console.print(
            f"[yellow]No unwind command for {client_name}, skipping...[/yellow]"
        )
        return

    console.print(f"[bold]Unwinding {client_name} to block {block}...[/bold]")

    image = get_docker_image(client_name, version)
    snapshot_path = get_snapshot_path(client_name, data_dir)

    run_docker(
        image,
        unwind_cmd,
        volumes={str(snapshot_path): "/data"},
        remove=True,
    )

    console.print(f"[green]Unwind complete[/green]")


def start_node(
    client_name: str,
    network: str,
    data_dir: str,
    version: str = "latest",
    container_name: str = "bench-node",
) -> str:
    """Start an execution client node for benchmarking.

    Returns container ID.
    """
    validate_client_network(client_name, network)

    image = get_docker_image(client_name, version)
    node_cmd = get_node_cmd(client_name, network, datadir="/data")
    snapshot_path = get_snapshot_path(client_name, data_dir)

    console.print(f"[bold]Starting {client_name} node...[/bold]")
    console.print(f"  Image: {image}")
    console.print(f"  Data: {snapshot_path}")

    container_id = run_docker(
        image,
        node_cmd,
        volumes={str(snapshot_path): "/data"},
        ports={HTTP_PORT: HTTP_PORT, ENGINE_PORT: ENGINE_PORT},
        detach=True,
        name=container_name,
    )

    console.print(f"[green]Node started: {container_id[:12]}[/green]")
    return container_id


def stop_node(container_name: str = "bench-node") -> None:
    """Stop the benchmark node."""
    console.print("[dim]Stopping node...[/dim]")
    docker_stop(container_name)
    console.print("[green]Node stopped[/green]")
    docker_rm(container_name)


def wait_for_node_ready(timeout: int = 120) -> None:
    """Wait for node to be ready to accept requests."""
    console.print("[dim]Waiting for node to be ready...[/dim]")

    start = time.time()
    while time.time() - start < timeout:
        try:
            # Check HTTP RPC (no JWT required)
            result = run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}',
                    f"http://localhost:{HTTP_PORT}",
                ],
                check=False,
                capture=True,
            )
            if result.returncode == 0 and "result" in result.stdout:
                console.print("[green]Node is ready[/green]")
                return
        except Exception:
            pass
        time.sleep(2)

    raise TimeoutError(f"Node not ready after {timeout} seconds")


def run_reth_bench(
    network: str,
    from_block: int,
    to_block: int,
    output_dir: Path,
    jwt_secret: Path,
) -> Path:
    """Run reth-bench new-payload-fcu.

    Returns path to output file.
    """
    rpc_url = get_rpc_url(network)
    output_file = output_dir / f"bench_{from_block}_{to_block}.json"

    console.print(f"[bold]Running reth-bench from {from_block} to {to_block}...[/bold]")

    run(
        [
            "reth-bench",
            "new-payload-fcu",
            "--rpc-url",
            rpc_url,
            "--from",
            str(from_block),
            "--to",
            str(to_block),
            "--engine-rpc-url",
            f"http://localhost:{ENGINE_PORT}",
            "--jwt-secret",
            str(jwt_secret),
            "--output",
            str(output_file),
        ]
    )

    console.print(f"[green]Benchmark complete: {output_file}[/green]")
    return output_file


def run_benchmark(config: BenchmarkConfig) -> list[RunResult]:
    """Run a complete benchmark with multiple runs.

    Returns list of run results.
    """
    validate_client_network(config.client, config.network)

    run_id = generate_run_id()
    results_dir = Path(config.data_dir) / "results" / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold blue]Starting benchmark run: {run_id}[/bold blue]")
    console.print(f"  Client: {config.client} ({config.version})")
    console.print(f"  Network: {config.network}")
    console.print(f"  Blocks: {config.from_block} -> {config.to_block}")
    console.print(f"  Runs: {config.runs}")
    console.print()

    # Unwind to start block
    unwind_to_block(
        config.client,
        config.network,
        config.from_block,
        config.data_dir,
        config.version,
    )

    results: list[RunResult] = []

    for run_num in range(1, config.runs + 1):
        console.print(f"\n[bold]Run {run_num}/{config.runs}[/bold]")

        # Clear caches before each run
        clear_caches()
        time.sleep(2)

        # Start node
        start_time = time.time()
        container_id = start_node(
            config.client,
            config.network,
            config.data_dir,
            config.version,
        )

        try:
            # Wait for node to be ready
            wait_for_node_ready()

            # JWT secret is auto-generated by the client at <datadir>/jwt.hex
            snapshot_path = get_snapshot_path(config.client, config.data_dir)
            jwt_secret = snapshot_path / "jwt.hex"

            # Run benchmark
            output_file = run_reth_bench(
                config.network,
                config.from_block,
                config.to_block,
                results_dir,
                jwt_secret,
            )

            duration = time.time() - start_time

            results.append(
                RunResult(
                    run_number=run_num,
                    output_file=output_file,
                    duration_seconds=duration,
                )
            )

        finally:
            # Always stop node
            stop_node()

    # Save run metadata
    metadata = {
        "run_id": run_id,
        "client": config.client,
        "version": config.version,
        "network": config.network,
        "block_range": {
            "from": config.from_block,
            "to": config.to_block,
        },
        "runs": config.runs,
        "results": [
            {
                "run_number": r.run_number,
                "output_file": str(r.output_file),
                "duration_seconds": r.duration_seconds,
            }
            for r in results
        ],
    }

    metadata_file = results_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    console.print(f"\n[bold green]Benchmark complete![/bold green]")
    console.print(f"Results saved to: {results_dir}")

    return results
