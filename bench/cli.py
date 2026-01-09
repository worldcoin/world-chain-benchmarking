"""Command-line interface for benchmarking."""

import click
from rich.console import Console

from .benchmark import BenchmarkConfig, run_benchmark
from .clients import CLIENTS, validate_client_network
from .profiling import run_profiled_benchmark
from .results import upload_results
from .snapshots import download_snapshot

console = Console()

CLIENT_NAMES = list(CLIENTS.keys())
NETWORKS = ["ethereum-mainnet", "worldchain-mainnet"]
PROFILING_CLIENTS = ["reth", "op-reth"]


@click.group()
def cli():
    """Execution client benchmarking CLI."""
    pass


@cli.command()
@click.argument("client", type=click.Choice(CLIENT_NAMES))
@click.argument("network", type=click.Choice(NETWORKS))
@click.option("--from", "from_block", type=int, required=True, help="Start block")
@click.option("--to", "to_block", type=int, required=True, help="End block")
@click.option("--version", default="latest", help="Client version (tag, e.g., v1.0.0 or 'latest')")
@click.option("--runs", default=3, help="Number of benchmark runs")
@click.option("--data-dir", default="/data", help="Data directory")
@click.option("--beacon-api-url", envvar="BEACON_API_URL", required=True, help="Beacon API URL for fetching execution requests")
def run(client: str, network: str, from_block: int, to_block: int, version: str, runs: int, data_dir: str, beacon_api_url: str):
    """Run benchmark for a client on a network.

    Example:
        bench run op-reth worldchain-mainnet --from 24175000 --to 24176000
    """
    try:
        validate_client_network(client, network)
    except ValueError as e:
        raise click.ClickException(str(e))

    if from_block >= to_block:
        raise click.ClickException("--from must be less than --to")

    config = BenchmarkConfig(
        client=client,
        network=network,
        version=version,
        from_block=from_block,
        to_block=to_block,
        runs=runs,
        data_dir=data_dir,
        beacon_api_url=beacon_api_url,
    )

    run_benchmark(config)


@cli.command()
@click.argument("client", type=click.Choice(CLIENT_NAMES))
@click.argument("network", type=click.Choice(NETWORKS))
@click.option("--block", type=int, required=True, help="Block number for snapshot")
@click.option("--data-dir", default="/data", help="Data directory")
def snapshot(client: str, network: str, block: int, data_dir: str):
    """Download snapshot for a client/network.

    Example:
        bench snapshot op-reth worldchain-mainnet --block 24175000
    """
    try:
        validate_client_network(client, network)
    except ValueError as e:
        raise click.ClickException(str(e))

    download_snapshot(client, network, block, data_dir)


@cli.command()
@click.option("--results-dir", default="/data/results", help="Results directory")
@click.option("--bucket", required=True, help="S3 bucket name")
def upload(results_dir: str, bucket: str):
    """Upload benchmark results to S3.

    Example:
        bench upload --bucket my-results-bucket
    """
    # Find the most recent results directory
    from pathlib import Path
    results_path = Path(results_dir)

    if not results_path.exists():
        raise click.ClickException(f"Results directory not found: {results_dir}")

    # Find latest run
    run_dirs = sorted([d for d in results_path.iterdir() if d.is_dir()], reverse=True)
    if not run_dirs:
        raise click.ClickException(f"No results found in {results_dir}")

    latest_run = run_dirs[0]
    console.print(f"Uploading results from: {latest_run}")

    upload_results(str(latest_run), bucket)


@cli.command()
@click.argument("client", type=click.Choice(PROFILING_CLIENTS))
@click.option("--from", "from_block", type=int, required=True, help="Start block")
@click.option("--to", "to_block", type=int, required=True, help="End block")
@click.option("--profiler", type=click.Choice(["perf", "samply"]), default="perf", help="Profiler to use")
@click.option("--network", default="ethereum-mainnet", type=click.Choice(NETWORKS), help="Network")
@click.option("--version", default="latest", help="Client version")
@click.option("--data-dir", default="/data", help="Data directory")
@click.option("--beacon-api-url", envvar="BEACON_API_URL", required=True, help="Beacon API URL for fetching execution requests")
def profile(client: str, from_block: int, to_block: int, profiler: str, network: str, version: str, data_dir: str, beacon_api_url: str):
    """Run profiled benchmark (reth/op-reth only).

    Example:
        bench profile reth --from 19000000 --to 19000100 --profiler perf
    """
    try:
        validate_client_network(client, network)
    except ValueError as e:
        raise click.ClickException(str(e))

    if from_block >= to_block:
        raise click.ClickException("--from must be less than --to")

    run_profiled_benchmark(
        client_name=client,
        network=network,
        from_block=from_block,
        to_block=to_block,
        data_dir=data_dir,
        beacon_api_url=beacon_api_url,
        profiler=profiler,
        version=version,
    )


if __name__ == "__main__":
    cli()
