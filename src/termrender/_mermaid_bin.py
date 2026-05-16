"""Resolve the ``mermaid-ascii`` executable.

Prefers the vendored build from pinned upstream master (commit ``6fffb8e``,
2026-04-27) under ``_bin/mermaid-ascii-<os>-<arch>``; this carries the
master-only flowchart fixes the PyPI wheel (capped at 1.2.0) lacks. Falls back
to a ``mermaid-ascii`` on PATH (the PyPI ``mermaid-ascii`` wheel) for platforms
not vendored here.

Rebuild vendored binaries with ``scripts/build-mermaid-ascii.sh``.
"""

from __future__ import annotations

import os
import platform
from functools import lru_cache

_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bin")

_OS_MAP = {"darwin": "darwin", "linux": "linux", "windows": "windows"}
_ARCH_MAP = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "x86_64": "amd64",
    "amd64": "amd64",
}


def _platform_tag() -> str:
    osname = _OS_MAP.get(platform.system().lower(), platform.system().lower())
    arch = _ARCH_MAP.get(platform.machine().lower(), platform.machine().lower())
    return f"{osname}-{arch}"


@lru_cache(maxsize=1)
def mermaid_ascii_bin() -> str:
    """Path to the vendored mermaid-ascii, or ``"mermaid-ascii"`` for PATH lookup."""
    vendored = os.path.join(_BIN_DIR, f"mermaid-ascii-{_platform_tag()}")
    if os.path.isfile(vendored) and os.access(vendored, os.X_OK):
        return vendored
    return "mermaid-ascii"
