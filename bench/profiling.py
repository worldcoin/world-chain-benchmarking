"""Profiling support for reth/op-reth using perf and samply."""

import shutil
import time
from pathlib import Path

from rich.console import Console

from .clients import get_client
from .snapshots import extract_archive, get_archive_path, get_rpc_url
from .utils import clear_caches, docker_stop, generate_run_id, run, run_docker

console = Console()

# Profiling-capable clients
PROFILING_CLIENTS = ("reth", "op-reth")

ENGINE_PORT = 8551


def validate_profiling_client(client_name: str) -> None:
    """Validate that a client supports profiling."""
    if client_name not in PROFILING_CLIENTS:
        valid = ", ".join(PROFILING_CLIENTS)
        raise ValueError(f"Profiling only supported for: {valid}")


def install_profiling_tools() -> None:
    """Install perf, samply, and inferno for flamegraph generation."""
    console.print("[bold]Installing profiling tools...[/bold]")

    # Install perf (best effort - might already be installed)
    run(
        ["apt-get", "install", "-y", "linux-tools-common", "linux-tools-generic"],
        sudo=True,
        check=False,
    )

    # Install samply via cargo
    run(["cargo", "install", "samply"], check=False)

    # Install inferno for flamegraph generation
    run(["cargo", "install", "inferno"], check=False)

    console.print("[green]Profiling tools installed[/green]")


def configure_profiling() -> None:
    """Configure system for profiling."""
    console.print("[dim]Configuring system for profiling...[/dim]")

    # Allow perf for current user
    run(["sh", "-c", "echo -1 > /proc/sys/kernel/perf_event_paranoid"], sudo=True, check=False)

    console.print("[green]System configured for profiling[/green]")


def run_profiled_benchmark(
    client_name: str,
    network: str,
    from_block: int,
    to_block: int,
    data_dir: str,
    beacon_api_url: str,
    profiler: str = "perf",
    version: str = "latest",
) -> Path:
    """Run a profiled benchmark.

    Note: This runs the node natively (not in Docker) to enable profiling.
    Extracts a fresh copy of the snapshot archive for the profiling run.

    Args:
        client_name: Client to profile (reth or op-reth)
        network: Network name
        from_block: Start block
        to_block: End block
        data_dir: Data directory
        profiler: 'perf' or 'samply'
        version: Client version

    Returns:
        Path to profiling output directory
    """
    validate_profiling_client(client_name)
    get_client(client_name).validate_network(network)

    run_id = generate_run_id()
    output_dir = Path(data_dir) / "profiling" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = get_archive_path(client_name, data_dir)
    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive_path}\n"
            f"Run 'bench snapshot {client_name} {network} --block <N>' first."
        )

    console.print(f"\n[bold blue]Starting profiled benchmark: {run_id}[/bold blue]")
    console.print(f"  Client: {client_name} ({version})")
    console.print(f"  Network: {network}")
    console.print(f"  Blocks: {from_block} -> {to_block}")
    console.print(f"  Profiler: {profiler}")
    console.print(f"  Archive: {archive_path}")
    console.print()

    # Extract fresh copy of archive for this run
    run_data_dir = Path(data_dir) / "runs" / f"profile_{run_id}"
    extract_archive(archive_path, run_data_dir)

    try:
        # Configure system
        configure_profiling()

        # Clear caches
        clear_caches()

        # For profiling, we need to run the node natively (not in Docker)
        # This requires reth/op-reth to be installed locally
        rpc_url = get_rpc_url(network)

        # Get the binary name
        binary = "op-reth" if client_name == "op-reth" else "reth"

        # Build node command
        node_cmd = get_client(client_name).get_node_cmd(network, datadir=str(run_data_dir))
        full_node_cmd = [binary] + node_cmd

        console.print(f"[bold]Starting {client_name} node with profiling...[/bold]")

        if profiler == "perf":
            # Run with perf record
            perf_output = output_dir / "perf.data"
            profiled_cmd = [
                "perf", "record",
                "-F", "99",  # 99 Hz sampling
                "-g",  # Call graph
                "-o", str(perf_output),
                "--",
            ] + full_node_cmd

            # Start node in background
            import subprocess
            node_process = subprocess.Popen(
                profiled_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                # Wait for node to be ready
                console.print("[dim]Waiting for node to be ready...[/dim]")
                time.sleep(30)  # Give node time to start

                # Run reth-bench
                console.print(f"[bold]Running reth-bench from {from_block} to {to_block}...[/bold]")
                bench_output = output_dir / "bench.json"
                run([
                    "reth-bench", "new-payload-fcu",
                    "--rpc-url", rpc_url,
                    "--from", str(from_block),
                    "--to", str(to_block),
                    "--engine-rpc-url", f"http://localhost:{ENGINE_PORT}",
                    "--output", str(bench_output),
                    "--full-requests",
                    "--beacon-api-url", beacon_api_url,
                ])

            finally:
                # Stop node
                console.print("[dim]Stopping node...[/dim]")
                node_process.terminate()
                node_process.wait(timeout=30)

            # Generate flamegraph
            console.print("[dim]Generating flamegraph...[/dim]")
            flamegraph_svg = output_dir / "flamegraph.svg"
            run(
                f"perf script -i {perf_output} | inferno-collapse-perf | inferno-flamegraph > {flamegraph_svg}",
                check=False,
            )

        elif profiler == "samply":
            # Run with samply
            samply_output = output_dir / "samply.json"
            profiled_cmd = [
                "samply", "record",
                "-o", str(samply_output),
                "--",
            ] + full_node_cmd

            import subprocess
            node_process = subprocess.Popen(
                profiled_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                console.print("[dim]Waiting for node to be ready...[/dim]")
                time.sleep(30)

                console.print(f"[bold]Running reth-bench from {from_block} to {to_block}...[/bold]")
                bench_output = output_dir / "bench.json"
                run([
                    "reth-bench", "new-payload-fcu",
                    "--rpc-url", rpc_url,
                    "--from", str(from_block),
                    "--to", str(to_block),
                    "--engine-rpc-url", f"http://localhost:{ENGINE_PORT}",
                    "--output", str(bench_output),
                    "--full-requests",
                    "--beacon-api-url", beacon_api_url,
                ])

            finally:
                console.print("[dim]Stopping node...[/dim]")
                node_process.terminate()
                node_process.wait(timeout=30)

        else:
            raise ValueError(f"Unknown profiler: {profiler}")

        console.print(f"\n[bold green]Profiling complete![/bold green]")
        console.print(f"Results saved to: {output_dir}")

    finally:
        # Clean up extracted data
        console.print(f"[dim]Cleaning up {run_data_dir}...[/dim]")
        shutil.rmtree(run_data_dir, ignore_errors=True)

    return output_dir
