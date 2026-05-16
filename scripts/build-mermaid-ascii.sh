#!/usr/bin/env bash
# Build the vendored mermaid-ascii binary from pinned upstream master.
#
# Usage: scripts/build-mermaid-ascii.sh
#
# Produces src/termrender/_bin/mermaid-ascii-<os>-<arch> for the *host*
# platform. Run on each target platform (or with GOOS/GOARCH set) to refresh
# the vendored binaries. Requires a Go toolchain (>=1.21).
#
# Why vendored: the PyPI `mermaid-ascii` wheel only ships up to 1.2.0, which
# lacks the master-only flowchart fixes (multiline node labels, duplicate /
# bidirectional edge-label separation, subgraph titles, wide-rune label
# widths). termrender prefers this binary and falls back to the PyPI wheel's
# `mermaid-ascii` on PATH for platforms not vendored here.
set -euo pipefail

# Pinned upstream commit (github.com/AlexanderGrooff/mermaid-ascii master).
PIN="6fffb8e2714acab2c4cb41c78894fabbc62cee56"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

git clone https://github.com/AlexanderGrooff/mermaid-ascii.git "$workdir/src"
git -C "$workdir/src" checkout --quiet "$PIN"

os="$(go env GOOS)"
arch="$(go env GOARCH)"
out="$repo_root/src/termrender/_bin/mermaid-ascii-${os}-${arch}"

mkdir -p "$(dirname "$out")"
( cd "$workdir/src" && go build -trimpath -o "$out" . )
chmod 755 "$out"

echo "Built $out"
"$out" --help >/dev/null && echo "Smoke test OK (pin ${PIN:0:7})"
