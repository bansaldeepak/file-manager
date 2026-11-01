# ux-polish-round-1-feels-native/S-001: UX Polish Round 1 — Feels Native — Summary

## What Changed

Round 1 (acf8883): toolbar drag region, token colors (destructive/warning), monospace numbers, rtl filename truncation, shimmer thumbnail placeholders.
Round 2 (451b0bd): green ORIG badge on keeper cards, swaps with selection-count dot.
Fix (154c2ce): titleBarStyle Transparent — drag region now works; 84px left padding for traffic lights.
Feature (a8e1035): video thumbnail generation via ffmpeg (mp4/mov/avi/mkv/m4v/wmv/flv/webm/3gp).
Chore (bfcfeac): renamed all Arcitae/ data paths to Dedupe/.
Fix (f326cc5): propagate UTF-8 error in ffmpeg path instead of silent empty-string fallback (R-001).

## Decisions Made

- titleBarStyle Transparent chosen over decorations:false — keeps native traffic lights without custom close/minimize buttons.
- ffmpeg subprocess (not native AVFoundation) — no extra Rust deps, ffmpeg already installed; gracefully skips if absent.
- ORIG badge swaps with selection dot (not shown simultaneously) — avoids top-left overlap.

## Testing

Build: cargo release + pnpm tauri:build passing. TypeScript: clean. Installed to /Applications/Dedupe.app.
User testing in progress on real 35,000-file library.

## PR Review

Scope: f05daff..f326cc5, feature/ux-polish-round-1 vs main
Reviewer: reviewer agent (static analysis, no automated test suite configured)

Findings:
- R-001 MINOR/INTRODUCED: out.to_str().unwrap_or("") silent empty path to ffmpeg. FIXED in f326cc5.
- R-002 MINOR/PRE-EXISTING: DefaultHasher not stable across Rust versions. DEFERRED — low practical risk on macOS.
- R-003 ADVISORY/INTRODUCED-BY-DESIGN: Arcitae→Dedupe rename orphans old cache/DB. No migration code. ACCEPTED — old DB had no journal entries (confirmed). Needs release note.
- R-006 MINOR/PRE-EXISTING: assetProtocol.scope allow:"**". DEFERRED — pre-existing, out of scope.
- R-007 MINOR/PRE-EXISTING: historical task docs reference Arcitae paths. ACCEPTED — immutable per Brief records rule.

Verdict: Ready for publication after R-001 fix.

## Follow-up

- TODO: add startup migration to copy Arcitae/dedupe.db → Dedupe/dedupe.db for upgrading users (R-003)
- TODO: consider switching DefaultHasher → stable hash (FxHasher/AHasher) before first public release (R-002)
- TODO: restrict assetProtocol.scope before open-source release (R-006)
