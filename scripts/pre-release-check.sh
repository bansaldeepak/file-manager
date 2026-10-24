#!/usr/bin/env bash
set -euo pipefail

echo "=== Pre-release checks ==="

echo "1. cargo build --workspace --release"
cargo build --workspace --release

echo "2. cargo test --workspace"
cargo test --workspace

echo "3. cargo audit"
cargo audit

echo "4. Python app still compiles"
source .venv/bin/activate
python3 -m py_compile app.py

echo "=== All checks passed ==="
