"""Overlay filesystem utilities for benchmark isolation."""

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .utils import run


@contextmanager
def overlay_mount(lower_dir: Path, overlay_base: Path, name: str) -> Iterator[Path]:
    """Mount kernel overlayfs and yield merged path.

    Creates an overlay filesystem that presents a merged view of the lower
    (read-only) directory with changes captured in the upper directory.
    When the context exits, the overlay is unmounted and cleaned up.

    Structure created at overlay_base:
    - upper/  (per-run writes, copy-on-write)
    - work/   (overlayfs internal scratch space)
    - merged/ (union view - what the container sees)

    Args:
        lower_dir: Base read-only directory (e.g., snapshot)
        overlay_base: Directory to create overlay structure in
        name: Name for the overlay mount (appears in mount output)

    Yields:
        Path to the merged directory
    """
    upper = overlay_base / "upper"
    work = overlay_base / "work"
    merged = overlay_base / "merged"

    for d in (upper, work, merged):
        d.mkdir(mode=0o777, parents=True, exist_ok=True)

    mount_opts = ",".join([
        f"lowerdir={lower_dir.resolve()}",
        f"upperdir={upper.resolve()}",
        f"workdir={work.resolve()}",
        "redirect_dir=on",
        "metacopy=on",
        "volatile",  # skip fsync - fine for ephemeral overlay
    ])

    try:
        run(
            ["mount", "-t", "overlay", name, "-o", mount_opts, str(merged.resolve())],
            sudo=True,
        )
        yield merged
    finally:
        run(["umount", str(merged.resolve())], sudo=True, check=False)
        shutil.rmtree(overlay_base, ignore_errors=True)
