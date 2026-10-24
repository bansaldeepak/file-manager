# Dedupe — local-first photo duplicate finder

A native macOS app for finding and removing duplicate photos. Built with Tauri 2, React, and Rust. Scans folders fast, shows duplicates in a contact sheet, and lets you quarantine copies safely — with a full restore path before anything is permanently deleted.

## What it does

1. **Scan** — Select one or more folders. The app does a three-pass scan: size filter → 4 KB prehash → full SHA-256. Only files that could be duplicates are fully hashed.
2. **Review** — Duplicates appear in a contact sheet grid. Each group shows the keeper (highest resolution / largest file / shallowest path) and its copies. Click a group to open the inspector with full metadata.
3. **Quarantine** — Select copies and move them to quarantine (`~/Library/Application Support/Dedupe/Quarantine/`). Nothing is deleted yet. Quarantined files are fully browsable and restorable.
4. **Restore** — Open the Quarantine tab. Select any file and restore it to its original location.
5. **Delete permanently** — Only from the Quarantine tab, after review. Requires an explicit confirmation. Frees disk space and cleans the thumbnail cache.

## Safety guarantees

- **Never deletes originals.** Permanent deletion is restricted to files inside the quarantine root.
- **Keeper is always preserved.** The keeper file in each group cannot be selected for quarantine.
- **Collision-safe moves.** If the destination path is occupied, the app appends a suffix rather than overwriting.
- **Operation journal.** Every quarantine move is written as `PENDING` before the filesystem operation and `COMPLETED` after. On startup, any interrupted operations are reconciled automatically.
- **SHA-256 verified moves.** The file is re-hashed at source before the move; mismatches abort the operation.

## Build from source

**Requirements:** macOS 13+, Rust 1.89+, Node 24+, pnpm.

```bash
git clone <repo>
cd image-dedupe/frontend
pnpm install
pnpm tauri:build          # produces target/release/bundle/macos/Dedupe.app
```

To run in dev mode (hot-reload frontend, debug Rust):
```bash
pnpm tauri:dev
```

## Dev commands

```bash
# Syntax check only (fast)
cargo build -p dedupe-app

# Frontend type check
pnpm tsc -b --noEmit

# Smoke test (scans a fixture folder, exits 0 if duplicates found)
./target/release/dedupe-app --smoke-test tests/fixtures/images
```

## Architecture

```
frontend/          React + TypeScript UI (Vite)
crates/
  core/            Scanner, hasher, grouper, quarantine logic (pure Rust)
  index/           SQLite schema, migrations, op_journal, file cache
  app/             Tauri command layer — wires core + index to the UI
```

**Scan pipeline (crates/app/src/commands/scan.rs):**
Walk dirs → stat + size filter → 4 KB prehash (rayon) → full SHA-256 + pixel hash (rayon, batched) → SQLite cache → emit `scan-groups` events progressively.

**Thumbnail cache (crates/app/src/thumbnail_cache.rs):**
Pre-generated during scan into `~/Library/Caches/Dedupe/thumbnails/`. Keyed by path hash + display size. Reads are ~1 ms (disk read + base64); decodes only on cache miss. Removed only on permanent delete.

**Operation journal (crates/index/src/op_journal.rs):**
State machine: `PENDING` → `COMPLETED` / `FAILED` / `ROLLED_BACK` / `DELETED`. Startup reconciliation heals interrupted moves.

## Match types

- **Exact** — SHA-256 identical bytes.
- **Similar** (pixel) — EXIF-corrected RGBA pixel hash identical (catches re-saves, format conversions at same resolution).

Perceptual hashing (pHash) for visually similar but resized/recompressed copies is planned as a follow-on.

## Data locations (macOS)

| Path | Contents |
|------|----------|
| `~/Library/Application Support/Dedupe/dedupe.db` | Scan cache + operation journal |
| `~/Library/Application Support/Dedupe/Quarantine/` | Quarantined files |
| `~/Library/Caches/Dedupe/thumbnails/` | Thumbnail JPEG cache |
| `~/Library/Logs/Dedupe/` | Rotating app logs |

## Contributing

Open issues and PRs are welcome. Before contributing, read `AGENTS.md` for coding conventions. The core crate has no Tauri dependency — logic can be tested without a UI.

Keep the safety invariants: never delete originals, always verify SHA-256 before moves, always write journal entries before filesystem operations.
