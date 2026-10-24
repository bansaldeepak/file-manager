#!/usr/bin/env bash
# Smoke test for the packaged Arcitae Dedupe .app.
# Usage: ./scripts/smoke-test.sh [/path/to/Arcitae\ Dedupe.app] [fixture_dir]
set -euo pipefail

APP_PATH="${1:-target/release/bundle/macos/Arcitae Dedupe.app}"
FIXTURE_DIR="${2:-tests/fixtures/images}"

if [ ! -d "$FIXTURE_DIR" ]; then
    echo "FAIL: fixture directory not found: $FIXTURE_DIR"
    echo "      Run: python tests/fixtures/gen_fixtures.py"
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "FAIL: .app not found at: $APP_PATH"
    echo "      Build first: pnpm tauri build"
    exit 1
fi

BINARY="$APP_PATH/Contents/MacOS/arcitae-dedupe"
if [ ! -x "$BINARY" ]; then
    echo "FAIL: binary not executable: $BINARY"
    exit 1
fi

echo "Running smoke test..."
echo "  app:      $APP_PATH"
echo "  fixtures: $FIXTURE_DIR"

"$BINARY" --smoke-test "$FIXTURE_DIR"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
    echo "=== Smoke Test PASSED ==="
else
    echo "=== Smoke Test FAILED (exit $STATUS) ==="
fi
exit "$STATUS"
