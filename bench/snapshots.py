"""Snapshot download and management."""

import os
from pathlib import Path

from rich.console import Console

from .clients import validate_client_network
from .utils import run

console = Console()

# Network definitions
NETWORKS = {
    "ethereum-mainnet": {
        "chain_id": 1,
        "rpc_env": "ETH_RPC_URL",
    },
    "worldchain-mainnet": {
        "chain_id": 480,
        "rpc_env": "WLD_RPC_URL",
    },
}

# Snapshot sources
ETHPANDAOPS_BASE = "https://snapshots.ethpandaops.io"
WORLDCHAIN_BUCKET = "jt-benchmarking-snapshots-0c836de28786b6f1"


def get_rpc_url(network: str) -> str:
    """Get RPC URL for a network from environment."""
    if network not in NETWORKS:
        raise ValueError(f"Unknown network: {network}")

    env_var = NETWORKS[network]["rpc_env"]
    url = os.environ.get(env_var)
    if not url:
        raise ValueError(f"Environment variable {env_var} not set for network {network}")
    return url


def get_snapshot_url(client_name: str, network: str, block: int) -> tuple[str, str]:
    """Get snapshot URL and compression type.

    Returns:
        (url, compression) where compression is 'zst' or 'lz4'
    """
    validate_client_network(client_name, network)

    if network == "ethereum-mainnet":
        # ethpandaops snapshots
        url = f"{ETHPANDAOPS_BASE}/mainnet/{client_name}/{block}/snapshot.tar.zst"
        return url, "zst"

    elif network == "worldchain-mainnet":
        # World Chain S3 bucket
        # Map client names to snapshot names
        snapshot_name = client_name
        if client_name == "op-reth":
            snapshot_name = "reth"  # op-reth uses reth snapshots

        url = f"s3://{WORLDCHAIN_BUCKET}/{snapshot_name}_{block}.tar.lz4"
        return url, "lz4"

    raise ValueError(f"No snapshot source for {client_name} on {network}")


def download_snapshot(
    client_name: str,
    network: str,
    block: int,
    data_dir: str,
    connections: int = 16,
) -> Path:
    """Download a snapshot archive (without extracting).

    Args:
        client_name: Client name (reth, op-reth, etc.)
        network: Network name
        block: Block number for snapshot
        data_dir: Base data directory
        connections: Parallel download connections

    Returns:
        Path to downloaded archive file
    """
    validate_client_network(client_name, network)

    url, compression = get_snapshot_url(client_name, network, block)
    archive_dir = Path(data_dir) / "archives" / client_name
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_path = archive_dir / f"snapshot.tar.{compression}"

    console.print(f"[bold]Downloading snapshot for {client_name} on {network}...[/bold]")
    console.print(f"  URL: {url}")
    console.print(f"  Archive: {archive_path}")

    # Build download command
    if url.startswith("s3://"):
        # S3 download
        download_cmd = f"s3fcp s3 '{url}'"
    else:
        # HTTP download with parallel connections
        download_cmd = f"s3fcp http -c {connections} --chunk-size 100MB '{url}'"

    # Download to archive file (no extraction)
    full_cmd = f"{download_cmd} > '{archive_path}'"

    run(["sh", "-c", full_cmd])

    console.print(f"[green]Archive downloaded to {archive_path}[/green]")
    return archive_path


def extract_archive(archive_path: Path, output_dir: Path) -> None:
    """Extract a snapshot archive to a directory.

    Args:
        archive_path: Path to the archive file (.tar.zst or .tar.lz4)
        output_dir: Directory to extract to
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect compression from extension
    suffix = archive_path.suffix
    if suffix == ".zst":
        decompress = "zstd"
    elif suffix == ".lz4":
        decompress = "lz4"
    else:
        raise ValueError(f"Unknown archive extension: {suffix}")

    console.print(f"[bold]Extracting archive...[/bold]")
    console.print(f"  Archive: {archive_path}")
    console.print(f"  Output: {output_dir}")

    full_cmd = f"tar -I {decompress} -xf '{archive_path}' -C '{output_dir}'"
    run(["sh", "-c", full_cmd])

    console.print(f"[green]Extracted to {output_dir}[/green]")


def verify_snapshot(path: Path, client_name: str) -> bool:
    """Verify snapshot directory structure.

    Returns True if snapshot looks valid.
    """
    if client_name in ("reth", "op-reth"):
        # Reth expects db directory
        return (path / "db").exists()

    elif client_name == "nethermind":
        # Nethermind expects nethermind_db
        return (path / "nethermind_db").exists()

    elif client_name in ("geth", "op-geth"):
        # Geth expects geth/chaindata
        return (path / "geth" / "chaindata").exists()

    return True  # Unknown client, assume valid


def get_archive_path(client_name: str, data_dir: str) -> Path:
    """Get the archive path for a client.

    Returns the path where the archive should exist.
    Checks for both .zst and .lz4 extensions.
    """
    archive_dir = Path(data_dir) / "archives" / client_name

    # Check for existing archive with either extension
    for ext in ("zst", "lz4"):
        path = archive_dir / f"snapshot.tar.{ext}"
        if path.exists():
            return path

    # Default to zst if no archive exists yet
    return archive_dir / "snapshot.tar.zst"
