#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

CLIENTS = {
    "Reth": Path("results/ethereum-mainnet/reth/20260113-234040-eb462edd"),
    "Nethermind": Path("results/ethereum-mainnet/nethermind/20260112-161614-122021d1"),
    "Geth": Path("results/ethereum-mainnet/geth/20260114-143331-9241ad6f"),
}


def load_raw_runs(base_path: Path) -> pd.DataFrame:
    """Load raw data from all runs and compute proper per-run MGas/s, then average."""
    runs = []
    for run_dir in sorted(base_path.glob("[0-9]*")):
        df = pd.read_csv(run_dir / "combined_latency.csv")
        df["mgas_per_sec"] = df["gas_used"] / df["total_latency"]
        df["run"] = int(run_dir.name)
        runs.append(df)

    combined = pd.concat(runs)

    aggregated = (
        combined.groupby("block_number")
        .agg({
            "mgas_per_sec": ["mean", "std"],
            "new_payload_latency": ["mean", "std"],
            "fcu_latency": ["mean", "std"],
            "gas_used": "first",
        })
        .reset_index()
    )
    aggregated.columns = [
        "block_number", "mgas_mean", "mgas_std",
        "new_payload_mean", "new_payload_std",
        "fcu_mean", "fcu_std", "gas_used",
    ]
    return aggregated


def plot_metric(ax, data: dict[str, pd.DataFrame], metric: str, ylabel: str, title: str, scale: float = 1.0):
    """Plot a metric for all clients with mean line and stddev shading."""
    stats_lines = []
    for i, (name, df) in enumerate(data.items()):
        color = COLORS[i % len(COLORS)]
        mean_col = f"{metric}_mean"
        std_col = f"{metric}_std"

        ax.plot(df["block_number"], df[mean_col] / scale, label=name, color=color, linewidth=1.5)
        ax.fill_between(
            df["block_number"],
            (df[mean_col] - df[std_col]) / scale,
            (df[mean_col] + df[std_col]) / scale,
            color=color, alpha=0.2,
        )

        mean_val = df[mean_col].mean() / scale
        std_val = df[mean_col].std() / scale
        if scale == 1:
            stats_lines.append(f"{name}: μ={mean_val:.1f}, σ={std_val:.1f}")
        else:
            stats_lines.append(f"{name}: μ={mean_val:.1f}ms, σ={std_val:.1f}")

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.text(
        0.02, 0.98, "\n".join(stats_lines),
        transform=ax.transAxes, fontsize=10, verticalalignment="top",
        fontfamily="monospace", bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )


# Load all client data
data = {name: load_raw_runs(path) for name, path in CLIENTS.items()}

fig, axes = plt.subplots(3, 1, figsize=(14, 12))
fig.suptitle(
    "Execution Client Performance Comparison\nEthereum Mainnet Blocks 22830001-22830100",
    fontsize=14, fontweight="bold",
)

plot_metric(axes[0], data, "mgas", "MGas/s", "Throughput (MGas/s)")
plot_metric(axes[1], data, "new_payload", "Latency (ms)", "New Payload Latency", scale=1000)
plot_metric(axes[2], data, "fcu", "Latency (ms)", "FCU Latency", scale=1000)
axes[2].set_xlabel("Block Number")

plt.tight_layout()
plt.savefig("results/client_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
