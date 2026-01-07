"""Results management and S3 upload."""

import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path

import boto3
from rich.console import Console

from .utils import run

console = Console()


@dataclass
class SystemInfo:
    """System information for benchmark reproducibility."""

    hostname: str
    instance_type: str | None
    instance_id: str | None
    region: str | None
    kernel: str
    cpu_model: str
    cpu_cores: int
    memory_gb: int


def collect_system_info() -> SystemInfo:
    """Collect system information."""

    # Basic info
    hostname = platform.node()
    kernel = platform.release()

    # CPU info
    cpu_model = "Unknown"
    cpu_cores = os.cpu_count() or 0
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu_model = line.split(":")[1].strip()
                    break
    except Exception:
        pass

    # Memory info
    memory_gb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    memory_gb = kb // (1024 * 1024)
                    break
    except Exception:
        pass

    # EC2 metadata (if available)
    instance_type = None
    instance_id = None
    region = None

    try:
        # Use IMDSv2
        token_result = run(
            ["curl", "-s", "-X", "PUT", "-H", "X-aws-ec2-metadata-token-ttl-seconds: 60",
             "http://169.254.169.254/latest/api/token"],
            check=False,
            capture=True,
        )
        if token_result.returncode == 0:
            token = token_result.stdout.strip()
            headers = ["-H", f"X-aws-ec2-metadata-token: {token}"]

            result = run(
                ["curl", "-s", *headers, "http://169.254.169.254/latest/meta-data/instance-type"],
                check=False,
                capture=True,
            )
            if result.returncode == 0:
                instance_type = result.stdout.strip()

            result = run(
                ["curl", "-s", *headers, "http://169.254.169.254/latest/meta-data/instance-id"],
                check=False,
                capture=True,
            )
            if result.returncode == 0:
                instance_id = result.stdout.strip()

            result = run(
                ["curl", "-s", *headers, "http://169.254.169.254/latest/meta-data/placement/region"],
                check=False,
                capture=True,
            )
            if result.returncode == 0:
                region = result.stdout.strip()
    except Exception:
        pass

    return SystemInfo(
        hostname=hostname,
        instance_type=instance_type,
        instance_id=instance_id,
        region=region,
        kernel=kernel,
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
    )


def upload_results(results_dir: str, bucket: str) -> str:
    """Upload benchmark results to S3.

    Args:
        results_dir: Directory containing results
        bucket: S3 bucket name

    Returns:
        S3 URL of uploaded results
    """
    results_path = Path(results_dir)

    if not results_path.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    # Read metadata to get run info
    metadata_file = results_path / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

    with open(metadata_file) as f:
        metadata = json.load(f)

    run_id = metadata["run_id"]
    client = metadata["client"]
    network = metadata["network"]

    # Add system info to metadata
    system_info = collect_system_info()
    metadata["system"] = {
        "hostname": system_info.hostname,
        "instance_type": system_info.instance_type,
        "instance_id": system_info.instance_id,
        "region": system_info.region,
        "kernel": system_info.kernel,
        "cpu_model": system_info.cpu_model,
        "cpu_cores": system_info.cpu_cores,
        "memory_gb": system_info.memory_gb,
    }

    # Save updated metadata
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    console.print(f"[bold]Uploading results to S3...[/bold]")
    console.print(f"  Bucket: {bucket}")
    console.print(f"  Run ID: {run_id}")

    # Upload using AWS CLI (more reliable for large files)
    s3_prefix = f"s3://{bucket}/{network}/{client}/{run_id}"

    run([
        "aws", "s3", "sync",
        str(results_path),
        s3_prefix,
    ])

    # Also copy metadata to "latest"
    latest_key = f"s3://{bucket}/{network}/{client}/latest.json"
    run([
        "aws", "s3", "cp",
        str(metadata_file),
        latest_key,
    ])

    console.print(f"[green]Results uploaded to {s3_prefix}[/green]")
    return s3_prefix


def list_results(results_dir: str) -> list[dict]:
    """List all benchmark results in a directory."""
    results_path = Path(results_dir)
    results = []

    if not results_path.exists():
        return results

    for run_dir in results_path.iterdir():
        if run_dir.is_dir():
            metadata_file = run_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    results.append(json.load(f))

    return sorted(results, key=lambda x: x.get("run_id", ""), reverse=True)
