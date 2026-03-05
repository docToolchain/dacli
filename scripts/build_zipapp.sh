#!/usr/bin/env bash
# Build a self-contained dacli.pyz using Python's zipapp module.
#
# The resulting .pyz file can be dropped into any directory and run with:
#   python3 dacli.pyz --help
#
# Requirements (build machine only): Python 3.12+, pip
# The .pyz is cross-platform (Linux, macOS, Windows) because all
# bundled dependencies are pure Python.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR=$(mktemp -d)
OUTPUT="${PROJECT_DIR}/dist/dacli.pyz"

cleanup() { rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

mkdir -p "$(dirname "$OUTPUT")"

echo "Installing CLI dependencies into build directory..."
pip install --quiet --target "$BUILD_DIR" click pyyaml pathspec

echo "Copying dacli source..."
cp -r "$PROJECT_DIR/src/dacli" "$BUILD_DIR/dacli"

# Create __main__.py for zipapp entry point
cat > "$BUILD_DIR/__main__.py" << 'ENTRY'
from dacli.cli import cli

cli()
ENTRY

echo "Building zipapp..."
python3 -m zipapp "$BUILD_DIR" -o "$OUTPUT" -p "/usr/bin/env python3" -c

echo ""
echo "Built: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
echo "Usage: python3 $OUTPUT --help"
