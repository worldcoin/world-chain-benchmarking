"""Benchmark execution using reth-bench."""

import csv
import json
import secrets
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from .clients import (
    get_docker_image,
    get_node_cmd,
    validate_client_network,
)
from .overlay import overlay_mount
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


def generate_jwt_secret(path: Path) -> None:
    """Generate a random JWT secret file for Engine API authentication.

    Format: 32 bytes as hex string with 0x prefix (66 chars total), no newline.
    """
    jwt_hex = "0x" + secrets.token_hex(32)
    # Write without trailing newline - some clients are sensitive to this
    path.write_bytes(jwt_hex.encode("ascii"))


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
    beacon_api_url: str


@dataclass
class RunResult:
    """Result of a single benchmark run."""

    run_number: int
    output_dir: Path
    duration_seconds: float


def start_node(
    client_name: str,
    network: str,
    datadir: Path,
    version: str = "latest",
    container_name: str = "bench-node",
) -> str:
    """Start an execution client node for benchmarking.

    Args:
        client_name: Name of the client (reth, geth, etc.)
        network: Network name (ethereum-mainnet, etc.)
        datadir: Path to mount as /data in the container
        version: Docker image version tag
        container_name: Name for the Docker container

    Returns:
        Container ID.
    """
    validate_client_network(client_name, network)

    image = get_docker_image(client_name, version)
    node_cmd = get_node_cmd(client_name, network, datadir="/data")

    console.print(f"[bold]Starting {client_name} node...[/bold]")
    console.print(f"  Image: {image}")
    console.print(f"  Data: {datadir}")

    container_id = run_docker(
        image,
        node_cmd,
        volumes={str(datadir): "/data"},
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
    beacon_api_url: str,
    run_number: int,
) -> Path:
    """Run reth-bench new-payload-fcu.

    Returns path to output directory for this run.
    """
    rpc_url = get_rpc_url(network)
    run_output_dir = output_dir / str(run_number)

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
            str(run_output_dir),
            "--full-requests",
            "--beacon-api-url",
            beacon_api_url,
        ]
    )

    console.print(f"[green]Benchmark complete: {run_output_dir}[/green]")
    return run_output_dir


def aggregate_results(results_dir: Path, num_runs: int) -> Path:
    """Aggregate benchmark results across multiple runs.

    Computes mean, median, and stddev for latency metrics across runs.

    Args:
        results_dir: Directory containing run subdirectories (1/, 2/, etc.)
        num_runs: Number of runs to aggregate

    Returns:
        Path to the aggregated results CSV file.
    """
    # Collect data from all runs, keyed by block_number
    # block_data[block_num] = {field: [values across runs]}
    block_data: dict[int, dict[str, list]] = {}

    latency_fields = ["new_payload_latency", "fcu_latency", "total_latency"]

    for run_num in range(1, num_runs + 1):
        csv_path = results_dir / str(run_num) / "combined_latency.csv"
        if not csv_path.exists():
            console.print(f"[yellow]Warning: {csv_path} not found, skipping[/yellow]")
            continue

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                block_num = int(row["block_number"])
                if block_num not in block_data:
                    block_data[block_num] = {
                        "transaction_count": int(row["transaction_count"]),
                        "gas_used": int(row["gas_used"]),
                    }
                    for field in latency_fields:
                        block_data[block_num][field] = []

                for field in latency_fields:
                    block_data[block_num][field].append(int(row[field]))

    # Compute statistics and write output
    output_path = results_dir / "aggregated_latency.csv"
    fieldnames = ["block_number", "mgas_per_sec"]
    for field in latency_fields:
        fieldnames.extend([f"{field}_mean", f"{field}_median", f"{field}_stddev"])

    all_mgas_per_sec: list[float] = []

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for block_num in sorted(block_data.keys()):
            data = block_data[block_num]
            row = {"block_number": block_num}
            for field in latency_fields:
                values = data[field]
                if len(values) > 0:
                    row[f"{field}_mean"] = round(statistics.mean(values), 2)
                    row[f"{field}_median"] = round(statistics.median(values), 2)
                    row[f"{field}_stddev"] = round(statistics.stdev(values), 2) if len(values) > 1 else 0
                else:
                    row[f"{field}_mean"] = 0
                    row[f"{field}_median"] = 0
                    row[f"{field}_stddev"] = 0

            # Compute MGas/s from gas_used and mean total latency (latency is in μs)
            total_latency_mean = row["total_latency_mean"]
            if total_latency_mean > 0:
                mgas = data["gas_used"] / total_latency_mean
                row["mgas_per_sec"] = round(mgas, 2)
                all_mgas_per_sec.append(mgas)
            else:
                row["mgas_per_sec"] = 0

            writer.writerow(row)

    console.print(f"[green]Aggregated results: {output_path}[/green]")

    # Print overall MGas/s summary
    if len(all_mgas_per_sec) > 1:
        avg_mgas = statistics.mean(all_mgas_per_sec)
        std_mgas = statistics.stdev(all_mgas_per_sec)
        console.print(f"\n[bold]Overall: {avg_mgas:.2f} ± {std_mgas:.2f} MGas/s[/bold]")
    return output_path


def run_benchmark(config: BenchmarkConfig) -> list[RunResult]:
    """Run a complete benchmark with multiple runs.

    Each run uses an isolated overlayfs mount so that the base snapshot
    remains unchanged between runs.

    Returns list of run results.
    """
    validate_client_network(config.client, config.network)

    run_id = generate_run_id()
    snapshot_path = get_snapshot_path(config.client, config.data_dir)
    results_dir = Path(config.data_dir) / "results" / config.network / config.client / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold blue]Starting benchmark run: {run_id}[/bold blue]")
    console.print(f"  Client: {config.client} ({config.version})")
    console.print(f"  Network: {config.network}")
    console.print(f"  Blocks: {config.from_block} -> {config.to_block}")
    console.print(f"  Runs: {config.runs}")
    console.print(f"  Snapshot: {snapshot_path}")
    console.print()

    results: list[RunResult] = []

    for run_num in range(1, config.runs + 1):
        console.print(f"\n[bold]Run {run_num}/{config.runs}[/bold]")

        # Setup overlay for this run
        overlay_base = Path(config.data_dir) / "overlays" / f"{run_id}_{run_num}"

        with overlay_mount(snapshot_path, overlay_base, f"bench-{run_num}") as merged_path:
            # Clear caches before each run
            clear_caches()
            time.sleep(2)

            # Generate JWT secret for Engine API auth
            jwt_secret = merged_path / "jwt.hex"
            generate_jwt_secret(jwt_secret)

            # Start node with overlay-mounted datadir
            start_time = time.time()
            container_id = start_node(
                config.client,
                config.network,
                merged_path,
                config.version,
            )

            try:
                # Wait for node to be ready
                wait_for_node_ready()

                # Run benchmark
                output_dir = run_reth_bench(
                    config.network,
                    config.from_block,
                    config.to_block,
                    results_dir,
                    jwt_secret,
                    config.beacon_api_url,
                    run_num,
                )

                duration = time.time() - start_time

                results.append(
                    RunResult(
                        run_number=run_num,
                        output_dir=output_dir,
                        duration_seconds=duration,
                    )
                )

            finally:
                # Always stop node before unmounting overlay
                stop_node()

        # Overlay is unmounted and cleaned up here, snapshot unchanged

    # Aggregate results across all runs
    aggregated_file = aggregate_results(results_dir, config.runs)

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
        "aggregated_results": str(aggregated_file),
        "results": [
            {
                "run_number": r.run_number,
                "output_dir": str(r.output_dir),
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
