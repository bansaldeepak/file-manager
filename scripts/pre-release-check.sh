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

echo "5. Smoke test (packaged .app)"
if [ -d "target/release/bundle/macos/Arcitae Dedupe.app" ]; then
    bash scripts/smoke-test.sh "target/release/bundle/macos/Arcitae Dedupe.app"
else
    echo "SKIP: packaged .app not found (run 'pnpm tauri build' to build it)"
fi

echo "=== All checks passed ==="
