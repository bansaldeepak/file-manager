# CEO Review: Native Desktop Migration PRD

**Skill:** /gstack-plan-ceo-review
**Date:** 2026-10-23
**PRD:** documentation/stories/native-desktop/PRD.md
**Branch:** none (no git repo)

## System Audit

| Item | Finding |
|------|---------|
| Git repo | No -- local directory only |
| Remote | None |
| Stashes | N/A |
| TODOs/FIXMEs | None in source |
| Codebase | 2,766 LOC: app.py (1254), folder_review.py (325), test_app.py (304), test_folder_review.py (883) |
| Tests | 64 passing (unittest + Streamlit AppTest) |
| Prior reviews | None found |
| Design doc | None |
| Binding decisions | None |

## Landscape (search unavailable -- in-distribution knowledge only)

**Layer 1 (tried and true):** Tauri 2 + React + Rust is a proven desktop stack for local-first apps. Czkawka is the established open-source Rust duplicate finder with reusable core. SQLite for local caching is standard. SHA-256 for exact dedup is universal.

**Layer 2 (new and popular):** Tauri 2 is mature but less battle-tested than Electron for complex UIs. Rust image ecosystem (image crate) is solid for decoding. pHash compatibility between Rust implementations and Python ImageHash is genuinely unproven. czkawka_core adoption outside its own GTK/Krokiet frontend is uncommon -- its API stability for third-party use is unknown.

**Layer 3 (first principles):** The real bottleneck is I/O on external storage, not CPU hashing speed. Rust won't fix a slow USB disk. The PRD correctly identifies this. Size-filtering before any hash work is the biggest win. The staged approach (exact-first, perception-later) matches the 80/20: most photo library duplicates are exact copies from imports/exports.

## 0A. Premise Challenge

**Real problem:** Owner has a large photo collection across folders and external drives. Comparing folders for duplicates is slow in the Streamlit app and the review UX requires too many clicks. The current app works but scanning 30K images takes ~43 seconds for visual grouping, and the web-based UI can't match native responsiveness for keyboard-driven review.

**Target outcome:** A native macOS app that opens a cached comparison in under 500ms, with keyboard-driven review, folder-level bulk actions, and the same safety guarantees (quarantine, restore, zero data loss).

**Do-nothing cost:** The Streamlit app works. The owner can keep using it. But it's slow to scan, sluggish on large libraries, requires a terminal + venv to launch, and the web UI adds latency to every interaction. For a personal tool used repeatedly, native is worth the investment.

**Does the plan solve the pain directly?** Mostly yes. The PRD targets the right problems: scan speed (size filtering, prehash, bounded workers), interaction latency (native UI, visible-only decoding, cached previews), and review efficiency (folder overview, keyboard shortcuts, batch actions). But it's a 6-stage migration of a working app, and the risk is that it becomes a multi-month project that never ships because parity is too hard to prove.

## 0B. Existing Code Leverage

| Sub-problem | Existing code | Reuse? |
|---|---|---|
| SHA-256 exact hashing | app.py:42-46, folder_review.py:27-41 | Port to Rust; golden fixture comparison |
| EXIF-corrected RGBA pixel hashing | app.py:49-55 | Port; parity tests needed |
| pHash (64-bit, threshold 6) | app.py:54 via imagehash.phash | Port; Rust pHash compatibility unproven |
| Folder planning/verification | folder_review.py:44-325 | Port logic; new Rust data structures |
| Quarantine/restore/collision handling | app.py ~300 lines | Port; operation journal replaces JSON history |
| Connected-component grouping | app.py visual grouping logic | Port; deterministic keeper ordering |
| Test fixtures and assertions | tests/ (883 + 304 lines) | Golden outputs for parity; test strategy ports |

No rebuild where refactoring works: the Rust migration is a genuine platform change, not a rewrite-for-fun. The Python code can't be refactored into a native desktop app. But the behavior and test expectations port directly as golden references.

## 0C. Dream State Mapping

```
CURRENT STATE                    THIS PLAN                     12-MONTH IDEAL
Python/Streamlit app             Tauri 2/React/Rust desktop    Fast native app with
1,254 LOC in app.py              6-stage migration              photo + video dedup,
64 tests, works but slow         Exact-first, staged parity     keyboard-driven review,
Web UI, terminal launch          Native .app, cached scans      one-click bulk cleanup,
30K images = 43s grouping        Target: <500ms cached open     handles 100K+ images,
JSON history, SQLite cache       Operation journal, new index   signed macOS release
```

This plan moves directly toward the 12-month ideal. The staging is sound: golden baseline proves the algorithms port correctly before any UI work.

## Reality Rows

REALITY: premise-table pass unverified=1 (Node version: PRD says 25.9.0, machine has 24.22.1) PRD.md:113
REALITY: already-done pass No prior implementation commits; PRD states "implementation has not started" PRD.md:3
REALITY: surface-check pass No CLI commands in PRD to verify (spec, not task list) PRD.md:1
REALITY: binding-decisions pass No binding decisions found via gstack-decision-search
REALITY: numbers finding Node version wrong; Rust/pnpm confirmed; perf targets estimated PRD.md:113
REALITY: deferred-asks pass Video/audio/Windows/cloud/auto-delete all explicitly deferred PRD.md:127
REALITY: pr-count n/a No git repo, no PR policy

### Premise Table

| Premise | Claim | File:line receipt | Verdict |
|---|---|---|---|
| Rust 1.89.0 active | "Rust 1.89.0 active" | PRD.md:113 | verified -- rustc --version confirms |
| Rust 1.95 installed | "1.95 also installed" | PRD.md:113 | verified -- rustup toolchain list confirms |
| Node 25.9.0 | "Node 25.9.0" | PRD.md:113 | WRONG -- machine has Node 24.22.1 |
| pnpm available | "pnpm" | PRD.md:113 | verified -- pnpm 11.22.0 |
| Apple CLI Tools | "Apple Command Line Tools" | PRD.md:113 | verified -- xcode-select -p confirms |
| 64 tests passing | "last passed 64 tests" | PRD.md:133 | verified per MEMORY.md |
| 43s visual grouping | "approximately 43 seconds" | MEMORY.md:line 2 | measured |
| 30,188 images | "30,188-row index" | MEMORY.md:line 1 | measured |
| 500ms cached open target | "Folder summary <=500 ms" | PRD.md:29 | estimated [re-measure before gate] |
| 200ms interaction target | "p95 <=200 ms" | PRD.md:28 | estimated [re-measure before gate] |

**unverified=1** (Node version is wrong)

## 0E. Mode Selection

**Selected: SELECTIVE EXPANSION** -- user choice via D1.

No new approach decision was needed.

## HOLD SCOPE Checks (0G step 1)

### 1. Complexity check
The PRD proposes 6 Rust crates + Tauri app + React frontend = 8 modules. For a single-developer personal tool, this is over-modularized. The PRD hedges: "This is the intended destination structure, not a requirement to create empty crates." A simpler structure -- 2-3 crates (core, index, app) -- achieves the same goal with less wiring. **Finding:** Defer crate decomposition; start with one `core` crate and split only when it helps.

### 2. Minimum changes for goal
Stages 1-4 (baseline, discovery, desktop preview, cleanup alpha) are the minimum viable path. Stage 5 (perceptual parity) is deferrable because exact dedup covers the majority case and the Python app remains available for visual similarity. Stage 6 (release polish) is partially deferrable -- packaging is needed, signing/notarization is nice-to-have.

### 3. Invariants preserved
All stated invariants (SHA-256, EXIF-RGBA pixel hashing, 64-bit pHash threshold 6, connected-component grouping, resolution/size/path keeper ordering, quarantine-only deletion, journal recovery) are present in the PRD. The two-folder comparison workflow from MEMORY.md is carried forward.

## 0F. Expansion Framing -- Cherry-Pick Candidates

| # | Proposal | Effort | Risk | Impact | User experience |
|---|----------|--------|------|--------|-----------------|
| 1 | Simplify to 2-3 crates instead of 6 | S | Low | Faster iteration, less boilerplate | You ship stages faster because there's less wiring between modules |
| 2 | Stage 5 deferral -- ship exact+cleanup before pHash parity | S | Low | Unblocks real testing sooner | You start using the native app weeks earlier; Python handles visual similarity meanwhile |
| 3 | Drag-and-drop folder selection alongside native pickers | M | Low | Medium | Drop a folder onto the app window instead of navigating the picker every time |
| 4 | Quick Look integration for previews (macOS native) | M | Medium | High | Preview images with spacebar like Finder; zero custom preview code for supported formats |
| 5 | Thumbnail caching with APNG/WebP instead of PNG | S | Low | Medium | 3-5x smaller thumbnail cache; faster loading on large libraries |
| 6 | Git init the project before implementation starts | S | Low | High | Version control from day 1; enables PRs, bisect, and rollback for every stage |

## 0G. Cherry-Pick Ceremony

Proposals presented one at a time below.

## Decision Ledger

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| D1-MODE | Review mode | N/A | SELECTIVE EXPANSION | approved | User choice via D1 |
| D2-CRATES | Crate structure | 6 crates per REQUIREMENTS.md s4 | 2-3 crates, split when needed | approved | User choice: start simple, split when real boundaries emerge |
| D3-STAGE5 | Stage 5 deferral | pHash parity before release | Ship exact+cleanup first, defer pHash | approved | User choice: defer pHash to post-MVP, Python handles visual similarity |
| D4-DND | Drag-and-drop folders | Native picker only | Add drag-and-drop alongside picker | approved | User choice: add to scope, effort S |
| D5-QUICKLOOK | Quick Look preview | Custom preview component | macOS Quick Look integration | approved | User choice: add to scope for full-size previews, effort M |
| D6-THUMBFMT | Thumbnail format | PNG thumbnails | WebP compressed thumbnails | approved | User choice: WebP at quality 80 for thumbnail cache, effort S |
| D7-GIT | Git init | No git repo | Initialize git before implementation | approved | User choice: git init with .gitignore before Stage 1 |
| D8-PHASH-SPEC | pHash vs REQUIREMENTS.md | REQUIREMENTS.md s3.1 includes pHash in MVP | Update REQUIREMENTS.md to match D3 deferral | approved | User choice: CEO plan is latest authority; annotate REQUIREMENTS.md s3.1 and s14 |

## Accepted Scope (added to this plan)

- D2: Start with 2-3 Rust crates (core + index + app), split when working code reveals real boundaries
- D3: Defer pHash/perceptual matching to post-MVP; ship exact + pixel-identical + cleanup first
- D4: Drag-and-drop folder selection alongside native pickers (Tauri 2 native support)
- D5: macOS Quick Look integration for full-size image previews (spacebar to preview)
- D6: WebP thumbnail cache instead of PNG (3-5x smaller, faster loading)
- D7: Git init with .gitignore before any implementation starts

## Deferred to TODOS.md

- Perceptual hashing (pHash) parity with Python ImageHash -- add after exact+cleanup MVP ships
- Video similarity detection -- after photo parity and safe file operations
- Audio duplicate detection
- Windows x64 build and installer
- Cloud scanning or account-based services
- Automatic permanent deletion
- Signed/notarized macOS releases (unless Apple Developer credentials available)

## NOT in scope

- (nothing rejected)

---

## Section 1: Architecture Review

**Current scope (SELECTIVE EXPANSION):**
- D1-MODE: SELECTIVE EXPANSION (user choice)
- D2-CRATES: 2-3 crates, split when needed (accepted)
- D3-STAGE5: Defer pHash to post-MVP (accepted)
- D4-DND: Drag-and-drop folder selection (accepted)
- D5-QUICKLOOK: Quick Look integration (accepted)
- D6-THUMBFMT: WebP thumbnail cache (accepted)
- D7-GIT: Git init before implementation (accepted)

### System Architecture

```
+--------------------------------------------------+
|                 Tauri Desktop App                  |
|  +----------------------------------------------+ |
|  |           React/TypeScript Frontend           | |
|  |  +--------+ +-----------+ +----------------+ | |
|  |  | Folder | | Contact   | | Comparison     | | |
|  |  | Nav    | | Sheet     | | Inspector      | | |
|  |  | (left) | | (center)  | | (right/QLook)  | | |
|  |  +--------+ +-----------+ +----------------+ | |
|  |       |          |               |            | |
|  |  +----+----------+---------------+-------+    | |
|  |  |  Tauri IPC (commands + events)        |    | |
|  |  +---------------------------------------+    | |
|  +----------------------------------------------+ |
|  +----------------------------------------------+ |
|  |          src-tauri (thin command layer)        | |
|  |  commands/ -> delegates to core + index        | |
|  |  events/   -> scan progress, cancellation      | |
|  +----------------------------------------------+ |
+--------------------------------------------------+
          |                    |
+---------v-------+  +--------v--------+
| crate: core     |  | crate: index    |
| - scanner       |  | - SQLite schema |
| - sha256 hash   |  | - migrations    |
| - pixel hash    |  | - file cache    |
| - grouping      |  | - op journal    |
| - keeper logic  |  | - review hist   |
| - quarantine    |  |                 |
| - restore       |  |                 |
| - collision     |  |                 |
+-----------------+  +-----------------+
```

### Data Flow (exact dedup scan)

```
Happy path:
  User selects folders -> Tauri command -> core::scanner walks dirs
  -> size-filter candidates -> prehash 4KB -> full SHA-256
  -> index::cache stores results -> core::grouping builds groups
  -> Tauri event streams progress -> frontend renders overview

Nil path (no folder selected):
  Frontend disables scan button, no command sent

Empty path (folder exists but contains 0 images):
  Scanner returns empty result -> frontend shows "No images found"
  -> no groups, no actions available

Error path (permission denied / disk unplugged):
  Scanner records per-file error -> continues other files
  -> index stores error column -> frontend shows skipped count
  -> affected groups marked incomplete
```

### Data Flow (quarantine)

```
Happy path:
  User checks copies -> confirm -> Tauri command
  -> core verifies identity(source) == expected
  -> core verifies hash(source) == hash(keeper)
  -> journal writes PENDING -> rename source to quarantine
  -> journal writes COMPLETED -> index removes row
  -> frontend updates group

Error path (file changed during verify):
  identity() != expected -> ValueError -> journal writes FAILED
  -> source preserved -> frontend shows per-file error

Error path (cross-volume):
  stat.st_dev differs -> copy+verify+remove workflow
  -> verify destination hash matches -> remove source
  -> if verify fails: remove destination, preserve source

Interrupted path:
  Journal has PENDING but no COMPLETED
  -> startup reconciliation checks source and destination
  -> if source exists: mark ROLLED_BACK
  -> if only destination exists: mark COMPLETED
  -> if both exist: verify destination, remove if matches, else alert
```

### Findings

| # | Finding | Severity |
|---|---------|----------|
| 1 | D5 Quick Look integration needs a Tauri command to invoke `qlmanage -p` or use the QLPreviewPanel API via objc bindings. Neither is documented in the PRD. Implementation owner must prove macOS sandbox compatibility with Quick Look panel. | **WARNING** |
| 2 | D4 drag-and-drop needs Tauri 2 `onDrop` event handling. The PRD mentions native pickers but not drop zones. No blocker, but the frontend component spec is missing. | OK |
| 3 | Rollback posture: if Stage 3 ships broken, uninstall the .app and continue using the Python app. The Python app is preserved by design. Rollback time: seconds. | OK |
| 4 | With D2 (2-3 crates), the `core` crate will be large. The key internal boundary is: scanner (I/O-bound) vs. grouping/keeper (CPU-bound) vs. quarantine (filesystem mutation). Keep these as separate modules within `core` for eventual extraction. | OK |

**Decision gate:** No issues requiring user decisions. Findings are implementation guidance.

---

## Section 2: Error & Rescue Map

Since no Rust code exists, this uses capability-level rows. Implementation owner must prove each rescue path.

```
CAPABILITY                    | WHAT CAN GO WRONG              | ERROR CLASS
------------------------------|--------------------------------|-----------------------
Scanner: walk directories     | Permission denied on folder    | std::io::Error(EACCES)
                              | Symlink loop                   | std::io::Error
                              | Path too long                  | std::io::Error
                              | Disk disconnected mid-scan     | std::io::Error(EIO/ENOENT)
------------------------------|--------------------------------|-----------------------
Scanner: stat file            | File deleted between walk/stat | std::io::Error(ENOENT)
                              | Not a regular file             | Custom(NotRegularFile)
------------------------------|--------------------------------|-----------------------
Hasher: read file             | File locked by another process | std::io::Error(EACCES)
                              | Corrupt/truncated read         | std::io::Error
                              | File changes during read       | Custom(FileChanged)
------------------------------|--------------------------------|-----------------------
Image decoder: open image     | Unsupported format (CR2, etc)  | image::ImageError
                              | Corrupt header                 | image::ImageError
                              | OOM on huge image              | std::alloc::Error / panic
------------------------------|--------------------------------|-----------------------
Index: SQLite operations      | DB locked (concurrent access)  | rusqlite::Error(Busy)
                              | Disk full                      | rusqlite::Error(Full)
                              | Schema migration failure       | Custom(MigrationFailed)
                              | WAL corruption                 | rusqlite::Error
------------------------------|--------------------------------|-----------------------
Quarantine: move file         | Cross-volume (st_dev differs)  | Custom(CrossVolume)
                              | Destination exists             | Custom(Collision)
                              | Source disappeared             | std::io::Error(ENOENT)
                              | Permission denied              | std::io::Error(EACCES)
                              | Journal write fails            | rusqlite::Error
------------------------------|--------------------------------|-----------------------
Restore: move back            | Original path occupied         | Custom(Collision)
                              | Quarantine file missing        | std::io::Error(ENOENT)
                              | Parent dir doesn't exist       | std::io::Error(ENOENT)
------------------------------|--------------------------------|-----------------------
Thumbnail: generate WebP      | Decoder can't open format      | image::ImageError
                              | Encoder fails (corrupt pixel)  | image::ImageError
                              | Cache dir full                 | std::io::Error
------------------------------|--------------------------------|-----------------------
Tauri IPC: command dispatch    | Serialization failure          | serde::Error
                              | Worker panicked                | Tauri error handler
------------------------------|--------------------------------|-----------------------

ERROR CLASS                    | RESCUED? | RESCUE ACTION               | USER SEES
-------------------------------|----------|-----------------------------|------------------
std::io::Error(EACCES)        | Y        | Skip file, record in index  | "N files skipped (permission denied)"
std::io::Error(ENOENT)        | Y        | Skip, invalidate cache      | File disappears from results
Custom(FileChanged)            | Y        | Abort operation, preserve   | "File changed, refresh required"
image::ImageError              | Y        | Store error in index        | Broken-image icon + tooltip
std::alloc::Error / OOM        | N <- GAP | Process crash               | App closes <- BAD
rusqlite::Error(Busy)          | Y        | Retry 3x with backoff       | Transparent
rusqlite::Error(Full)          | N <- GAP | Operation fails             | Unclear error <- BAD
Custom(CrossVolume)            | Y        | Copy-verify-remove workflow  | "Moving to quarantine..."
Custom(Collision)              | Y        | Suffix-based rename          | Shows new path
Custom(MigrationFailed)        | N <- GAP | App won't start             | Unclear error <- BAD
serde::Error                   | Y        | Return error to frontend    | Toast with error details
Tauri worker panic             | Y        | Tauri catches, returns err  | "Operation failed" toast
```

### CRITICAL GAPS

| # | Gap | Severity | Required fix |
|---|-----|----------|-------------|
| 1 | OOM on huge images (100MP+ panoramas). The `image` crate decodes to full RGBA in memory. A 100MP image = ~400MB. No memory limit specified. | **CRITICAL GAP** | Set a configurable max decode dimension (e.g., 32768x32768). Skip images exceeding it with a recorded error. |
| 2 | Disk-full during SQLite write. No rescue specified for SQLITE_FULL. | **WARNING** | Catch SQLITE_FULL, report "Disk full -- free space and retry", preserve in-flight data via WAL. |
| 3 | Schema migration failure on app startup. No fallback specified. | **WARNING** | Show a clear error dialog with the migration version that failed. Offer "Reset database" as a last resort (data loss for cache only, not source files). |

**Decision gate:** No user decisions needed. Implementation owner must address the 3 gaps above.

---

## Section 3: Security & Threat Model

| # | Threat | Likelihood | Impact | Mitigated? | Notes |
|---|--------|-----------|--------|------------|-------|
| 1 | Path traversal in quarantine/restore (e.g., `../../etc/passwd` in stored path) | Med | High | Partially | PRD REQUIREMENTS.md s8.2 says "protect against path traversal and symlink attacks." The Python `folder_review.py:20-24` validates with `identity()` and `resolve()`. Rust must replicate: canonicalize, assert within quarantine root, reject symlinks. |
| 2 | Symlink attack: attacker replaces quarantine target with symlink before move | Low | High | Yes (spec) | REQUIREMENTS.md s8.1: "Revalidate source existence, file identity signals." Python uses `O_NOFOLLOW` + `identity()`. Rust must use `O_NOFOLLOW` equivalent. |
| 3 | Frontend sends arbitrary path to Tauri delete command | Low | Critical | Yes (spec) | REQUIREMENTS.md s8.2: "Never trust a path supplied by the frontend without backend validation." Tauri capability scoping limits allowed paths. |
| 4 | Race condition: TOCTOU between verify and move | Low | Med | Partially | Python does pre-move + post-move identity check (`folder_review.py:299-302`). Rust journal provides recovery but the window still exists. |
| 5 | Personal file paths in logs | Low | Low | Yes (spec) | REQUIREMENTS.md s11: "Do not log image content or unnecessarily expose personal file paths." `tracing` strategy must filter paths. |
| 6 | Dependency supply chain (Tauri, image crate, rusqlite) | Low | High | Partially | REQUIREMENTS.md s4.2: "Review each dependency's license, maintenance status, security posture." No `cargo audit` or CI check specified. |
| 7 | Tauri capability over-scoping | Med | Med | Partial | REQUIREMENTS.md s11: "Restrict Tauri capabilities to the minimum required." Implementation must use scoped `fs` permissions, not `fs:allow-*`. |

### Findings

| # | Finding | Severity |
|---|---------|----------|
| 1 | No `cargo audit` in CI specified. Dependency vulnerability scanning is missing from Stage 6 exit evidence. | **WARNING** |
| 2 | TOCTOU between verify_plan and actual move is inheritable from Python. The journal-based recovery mitigates but doesn't prevent the race. Acceptable for a local single-user app. | OK |
| 3 | Tauri capability config not specified. Implementation must use folder-scoped `fs:allow-read` and `fs:allow-write` rather than blanket permissions. | **WARNING** |

**Decision gate:** No user decisions needed. Findings are implementation requirements.

---

## Section 4: Data Flow & Interaction Edge Cases

### Scan Data Flow

```
INPUT: user-selected folder paths
  |
  v
VALIDATION: paths exist, are directories, not symlinks, not overlapping
  |   nil: no selection -> scan button disabled
  |   empty: folder exists but contains 0 eligible files -> "No images"
  |   wrong type: file selected instead of dir -> picker prevents this
  v
TRANSFORM: walk -> stat -> size-filter -> prehash -> full hash
  |   error: per-file IO error -> skip, record error, continue
  |   timeout: user cancels -> safe boundary stop, partial results
  v
PERSIST: SQLite INSERT OR REPLACE per file
  |   error: SQLITE_FULL -> see Section 2 gap
  |   conflict: same path, different content -> UPDATE with new hash
  v
OUTPUT: Tauri event with group results -> frontend renders
  |   stale: cached results flagged with scan timestamp
  |   partial: cancelled scan shows completed portion
```

### Quarantine Data Flow

```
INPUT: array of (source_path, keeper_path, expected_sha256)
  |
  v
VALIDATION: all paths within scope, keeper not in selection
  |   nil: empty selection -> button disabled
  |   conflict: keeper selected -> reject with error
  v
VERIFY: for each pair: identity(source) == expected, hash matches
  |   error: file changed -> abort entire batch, zero moves
  |   partial: batch pre-verifies ALL before moving ANY
  v
JOURNAL: write PENDING entry per file
  |   error: journal write fails -> abort, no moves started
  v
MOVE: rename or copy-verify-remove per file
  |   error: permission denied -> record FAILED, continue others
  |   collision: destination exists -> suffix rename
  v
JOURNAL: write COMPLETED or FAILED per file
  |
  v
OUTPUT: results per file -> frontend updates affected groups
```

### Interaction Edge Cases

| Interaction | Edge Case | Handled? | How? |
|---|---|---|---|
| Folder selection | Double-click folder in picker | Yes | Native picker handles; no custom double-click |
| Folder selection (D4) | Drop file instead of folder | Need spec | Validate `event.paths`, reject non-directories |
| Start scan | Scan already running | Need spec | Disable button during scan, or queue second scan |
| Cancel scan | Cancel during hash of large file | Yes (PRD) | "Worker stops at safe boundaries" -- current chunk completes |
| Navigate folders | Navigate away during scan | Yes (PRD R4) | Background scan continues, no app rerender |
| Select copies | Select all then deselect keeper | Yes (PRD) | Keeper never in selection set by default |
| Confirm quarantine | Click confirm twice rapidly | Need spec | Disable button after first click; re-enable on result |
| Restore | Original path occupied | Yes (spec) | Suffix-based collision resolution |
| Restore | Quarantine folder deleted externally | Need spec | Journal shows PENDING, reconciliation detects missing file |
| Quick Look (D5) | Preview unsupported file | OK | Quick Look shows its own "no preview" placeholder |
| Thumbnail load | 10,000 thumbnails in view | Yes (PRD R5) | Virtualized; only visible thumbnails decode |
| Scope change | Change original folder during review | Yes (PRD) | Reset selections and confirmations |

### Findings

| # | Finding | Severity |
|---|---------|----------|
| 1 | Double-click/rapid-confirm on quarantine action not specified. Must disable the confirm button after first click. | **WARNING** |
| 2 | D4 drag-and-drop: no spec for dropping a file vs. folder. Must validate and reject non-directory drops. | OK |
| 3 | Concurrent scan handling not specified. Second scan request while one is running. Recommend: queue or reject with message. | OK |

**Decision gate:** No user decisions needed.

---

## Section 5: Code Quality Review

No Rust code exists. This reviews the PRD and REQUIREMENTS.md spec quality and the Python reference code quality for port.

### Spec Quality

| # | Finding | Severity |
|---|---------|----------|
| 1 | PRD Node version claim is wrong (25.9.0 vs actual 24.22.1). Factual error that could mislead toolchain pinning. | **WARNING** |
| 2 | REQUIREMENTS.md s4 proposes 6 crates. D2 accepted 2-3. REQUIREMENTS.md should be updated to reflect the accepted structure before implementation starts. | OK |
| 3 | PRD R9 includes pHash but D3 defers it. The PRD delivery sequence already puts pHash in Stage 5. Consistent with deferral. | OK |

### Python Reference Code Quality (for port)

| # | Pattern | Quality | Port note |
|---|---------|---------|-----------|
| 1 | `folder_review.py:identity()` -- pre/post identity checks with O_NOFOLLOW | Excellent | Port directly to Rust; this is the TOCTOU mitigation |
| 2 | `folder_review.py:hash_regular_file()` -- open-check-read-check pattern | Excellent | Port the three-stage verify pattern |
| 3 | `folder_review.py:validate_duplicate_scope()` -- overlap/symlink rejection | Good | Port; add Tauri capability scoping on top |
| 4 | `folder_review.py:move_directory()` -- exclusive reservation + cleanup | Good | Port; extend with journal integration |
| 5 | `app.py:signatures()` -- EXIF transpose + RGBA convert + dimension prefix | Good | Port with golden fixture parity tests |
| 6 | Over-engineering: REQUIREMENTS.md specifies 6 crates + 12 repo docs for a personal tool | Note | D2 addresses crate count. Open-source docs can be added at release. |

**Decision gate:** No issues. Implementation owner should update Node version in PRD.

---

## Section 6: Test Review

### Test Coverage Diagram

```
+-- STAGE 1: Baseline -----------------------------------------+
|  Unit: exact hash, pixel hash, keeper ordering, hamming dist  |
|  Golden: Python reference exporter -> JSON -> Rust comparison |
|  Parity: exact groups match, pixel groups match               |
+--------------------------------------------------------------+
          |
+-- STAGE 2: Discovery ----------------------------------------+
|  Unit: size filter, prehash, candidate filtering              |
|  Integration: cold scan, warm scan, cache invalidation        |
|  Cancellation: mid-scan cancel preserves partial results      |
|  Benchmark: SSD vs external timing, work counters             |
+--------------------------------------------------------------+
          |
+-- STAGE 3: Desktop Preview ----------------------------------+
|  Component: folder nav, contact sheet, comparison inspector   |
|  E2E: choose roots -> scan -> browse -> compare thumbnails    |
|  Keyboard: tab order, focus, spacebar preview (D5)            |
|  Launch: packaged .app starts without dev tools               |
+--------------------------------------------------------------+
          |
+-- STAGE 4: Cleanup Alpha ------------------------------------+
|  Unit: journal state machine transitions                      |
|  Integration: quarantine -> restore -> delete cycle           |
|  Fault: crash between journal PENDING and COMPLETED           |
|  Fault: disk disconnected mid-quarantine                      |
|  Edge: collision-safe restore, zero-image guard               |
|  Edge: cross-volume copy-verify-remove                        |
|  Scope: overlapping roots rejected, keeper protected          |
+--------------------------------------------------------------+
          |
+-- STAGE 6: Release ------------------------------------------+
|  Packaging: DMG on clean account                              |
|  Smoke: launch, scan, quarantine, restore on packaged .app    |
|  Accessibility: keyboard-only full workflow                   |
+--------------------------------------------------------------+
```

### Test Ambition Check

| Feature | 2am Friday test | Hostile QA test | Chaos test |
|---|---|---|---|
| Exact dedup | Golden fixtures: 100% group match | Unicode paths with emoji + spaces + max length | 50K files, cancel at 73%, resume |
| Quarantine | Move + restore + verify round-trip | Kill -9 between journal PENDING and rename | Unplug USB during cross-volume copy |
| Folder scope | Protected original never in results | Select original as duplicate root (must reject) | Delete original folder mid-verification |
| Cache | Warm scan reads 0 files for unchanged | Modify 1 file, verify only it re-hashes | Corrupt SQLite WAL, restart app |
| Thumbnails | Visible-only decode, 0 offscreen work | Load 10K group, scroll at 60fps | OOM: generate thumb for 100MP panorama |

### Findings

| # | Finding | Severity |
|---|---------|----------|
| 1 | No test specified for OOM on large image decode. Need a fixture with a very large image header (claimed dimensions) or actual large synthetic image. | **WARNING** |
| 2 | Cross-volume quarantine test not explicitly in Stage 4 exit evidence. The PRD mentions "collision-safe" but not cross-volume specifically. Implementation owner must prove copy-verify-remove with fault injection. | **WARNING** |
| 3 | D5 Quick Look has no testability spec. Keyboard test: spacebar on selected image invokes Quick Look panel. Component test: verify QLPreviewPanel API call. | OK |

**Decision gate:** No user decisions needed.

---

## Section 7: Performance Review

| # | Area | Finding | Severity |
|---|------|---------|----------|
| 1 | N+1 queries | SQLite index lookup per file during folder planning. Python already batches with `reference_index()` (folder_review.py:100-108). Rust must replicate: build hash-to-keeper map once, reuse across batch. | OK (pattern exists) |
| 2 | Memory: scan | 30K files x ~500 bytes metadata = ~15MB. Acceptable. Peak during grouping depends on group count, not file count. | OK |
| 3 | Memory: thumbnails | 30K x WebP ~20KB = ~600MB if all cached. Visible-only decode means ~50 in memory at once = ~1MB. D6 WebP helps disk, not RAM (thumbnails are decoded to pixels in the webview). | OK |
| 4 | Memory: image decode | Full RGBA decode for pixel hashing. 24MP image = ~96MB. With rayon parallelism, 4 concurrent = ~384MB. | **WARNING** -- bound concurrent image decodes to 2 or add memory-based throttling. |
| 5 | SQLite: journal writes | One INSERT per quarantine operation in a batch. Must use a single transaction for the batch, not one transaction per file. | OK (Python pattern: one commit per batch) |
| 6 | Slow paths | (1) Cold scan with full hashing: I/O bound, ~5-10 min for 30K on external USB. (2) First thumbnail generation for a folder: decode + resize + WebP encode. (3) Visual grouping (deferred per D3). | OK |
| 7 | Caching | Thumbnail cache keyed on (path, mtime, size). Index cache keyed on (path, size, mtime, analyzer_version). Both specified in REQUIREMENTS.md s5.3. | OK |
| 8 | External storage | PRD correctly identifies I/O as the bottleneck. Bounded workers (rayon thread pool) prevent saturating a slow USB disk. Need a configurable concurrency limit, not hardcoded. | **WARNING** |

### Top 3 Slowest Codepaths (estimated p99)

1. Cold scan of 30K images on external USB: 5-15 minutes (I/O bound)
2. First thumbnail generation for 1000-image folder: 30-60 seconds (decode + resize + encode)
3. Batch quarantine verification of 500 files: 10-30 seconds (re-hash all source + keeper files)

**Decision gate:** No user decisions needed.

---

## Section 8: Observability & Debuggability Review

| # | Area | Finding | Severity |
|---|------|---------|----------|
| 1 | Logging | REQUIREMENTS.md specifies `tracing` with path filtering. Need structured logs: scan_id, phase, file_count, error_count at INFO; per-file at DEBUG. | OK |
| 2 | Metrics | PRD specifies work counters: bytes_read, hashes_performed, decode_count, grouping_time, peak_memory. These double as observability. Must be exposed in UI (already in PRD success metrics). | OK |
| 3 | Debuggability | If a quarantine fails 3 weeks post-ship: journal has every operation with timestamp, source, destination, status. Sufficient for reconstruction. | OK |
| 4 | Runbooks | No runbook specified. For a personal tool, the journal IS the runbook: query it for PENDING/FAILED entries and manually resolve. | OK |
| 5 | Log rotation | No log rotation specified. `tracing` with `tracing-appender` can rotate, but for a desktop app, a single log file with size cap (~10MB) is sufficient. | **WARNING** -- specify max log size to prevent unbounded growth. |

### SELECTIVE EXPANSION: Observability for accepted cherry-picks

- D4 drag-and-drop: log dropped paths at DEBUG level for troubleshooting rejected drops
- D5 Quick Look: log invocation success/failure at INFO (did the panel open?)
- D6 WebP thumbnails: log cache hit/miss ratio at INFO per scan, total cache size at startup

**Decision gate:** No user decisions needed.

---

## Section 9: Deployment & Rollout Review

| # | Area | Finding | Severity |
|---|------|---------|----------|
| 1 | Migration safety | New SQLite schema, no existing native DB. No migration from Python DB specified (explicitly deferred in PRD). Schema versioning required from Stage 1. | OK |
| 2 | Feature flags | Not needed for a personal tool with staged delivery. Each stage is its own feature gate. | OK |
| 3 | Rollout order | Stage 1 (Rust CLI) -> 2 (discovery) -> 3 (desktop) -> 4 (cleanup). Correct: prove algorithms before UI, prove display before mutation. | OK |
| 4 | Rollback plan | Uninstall .app, continue using Python. Python app and data preserved throughout (PRD "Rollout and Deferred Scope"). Rollback time: seconds. | OK |
| 5 | Deploy-time risk | Not applicable -- local desktop app, not a server. Each build is independent. | OK |
| 6 | Packaging | Stage 6: DMG on clean Mac account. Unsigned apps trigger Gatekeeper. PRD correctly: "signing/notarization status disclosed." | OK |
| 7 | Post-install verification | No automated smoke test for packaged .app specified. | **WARNING** -- Stage 6 should include a scripted smoke test: launch .app, scan a fixture folder, verify result count, exit. |

### SELECTIVE EXPANSION: Deployment for accepted cherry-picks

D7 (git init) changes the deployment picture: git enables CI. Even without a remote, local git hooks can run `cargo test` pre-commit. Worth setting up in Stage 1.

**Decision gate:** No user decisions needed.

---

## Section 10: Long-Term Trajectory Review

| # | Area | Assessment |
|---|------|-----------|
| 1 | Technical debt | D2 (2-3 crates) is intentional debt: a larger `core` crate that may need splitting. This is good debt -- split when you feel the seam. D3 (defer pHash) is managed debt with the Python fallback. |
| 2 | Path dependency | Tauri 2 locks the frontend to a webview. If Tauri 3 changes APIs, migration work. But Tauri is the most mature Rust desktop framework. The core crate is framework-independent by design. |
| 3 | Knowledge concentration | Single developer. REQUIREMENTS.md and PRD are thorough enough for a second contributor. The Python reference + golden fixtures make the expected behavior clear. |
| 4 | Reversibility | 4/5 -- the native app is additive. Python app preserved. Worst case: abandon the native app, keep using Python. Only the time investment is lost. |
| 5 | Ecosystem fit | Tauri 2 + React + Rust is conventional for local-first desktop apps in 2026. No exotic choices. |
| 6 | 1-year question | A new engineer reading this codebase in 12 months would find: clear PRD, golden fixtures, parity tests, operation journal. The staging makes the progression obvious. |

### SELECTIVE EXPANSION: Trajectory for accepted cherry-picks

- D5 (Quick Look) creates a macOS-specific code path. When Windows support is added, this needs a platform abstraction or WIC equivalent. The PRD already defers Windows. Acceptable.
- D6 (WebP thumbnails) is portable. The `image` crate's WebP support works on all platforms.
- D4 (drag-and-drop) is portable via Tauri 2's cross-platform drag-and-drop events.

### Retrospective: Were the right cherry-picks accepted?

All 6 accepted proposals are low-risk, low-effort additions that improve the UX or reduce scope. None creates coupling concerns. D3 (defer pHash) is the most impactful -- it shortens the critical path significantly. D5 (Quick Look) is the only one with platform-specific risk, but it's well-bounded. No rejected expansions turned out to be load-bearing.

**Decision gate:** No issues.

---

## Section 11: Design & UX Review

The PRD has significant UI scope (three-pane desktop layout, folder navigation, contact sheet, comparison inspector, quarantine review).

### Information Architecture

User sees first: header with Original and Find Copies paths
User sees second: left pane folder navigation (overview of duplicate folders)
User sees third: center contact sheet (thumbnails of duplicate groups)
On demand: right pane comparison inspector (side-by-side or Quick Look)

### User Flow

```
+-------------------+     +------------------+     +-------------------+
| LAUNCH            |     | SCAN             |     | FOLDER OVERVIEW   |
| - Welcome / last  |---->| - Progress bar   |---->| - Ranked folders  |
|   session resume  |     | - Phase label    |     | - Coverage %      |
| - Choose folders  |     | - Cancel button  |     | - Bytes reclaimable|
|   (picker / D4)   |     | - Error count    |     | - Select folders  |
+-------------------+     +------------------+     +-------------------+
                                                          |
                          +------------------+            |
                          | THUMBNAIL REVIEW |<-----------+
                          | - Contact sheet  |
                          | - Check copies   |
                          | - Keeper marked  |
                          | - Page through   |
                          +------------------+
                                |
                          +------------------+     +-------------------+
                          | CONFIRM          |     | QUARANTINE        |
                          | - Move count     |---->| - Quarantined list|
                          | - Bytes          |     | - Preview (D5)    |
                          | - Retained locs  |     | - Restore         |
                          | - Zero-img guard |     | - Perm delete     |
                          +------------------+     +-------------------+
```

### Interaction State Coverage

| Feature | Loading | Empty | Error | Success | Partial |
|---|---|---|---|---|---|
| Folder selection | N/A | No folder chosen (buttons disabled) | Invalid folder (toast) | Paths shown in header | N/A |
| Scan | Progress bar + phase | 0 images found | Per-file errors + total | Groups available | Cancelled (partial results) |
| Folder overview | Skeleton rows | No duplicates found | Index read error | Ranked table | Some folders unscanned |
| Thumbnail grid | Placeholder shimmer | No matches in folder | Decode error (broken icon) | Thumbnails rendered | Mixed loaded/placeholder |
| Quarantine confirm | Verifying spinner | 0 selected (button disabled) | Verify failed (per-file) | All moved | Some failed, some moved |
| Quarantine list | Loading list | Empty quarantine | Read error | Full list | Partially restored |
| Quick Look (D5) | QL panel loading | Unsupported format (QL msg) | File missing | Preview shown | N/A |

### Findings

| # | Finding | Severity |
|---|---------|----------|
| 1 | No empty state design for "no duplicates found." Important for user confidence that the scan worked correctly. Show: "Scanned N files in M folders. No exact duplicates found." | **WARNING** |
| 2 | Keyboard shortcuts not enumerated. PRD says "keyboard navigation, visible focus" but doesn't list specific key bindings. Minimum: Tab (navigate), Space (Quick Look / D5), Enter (confirm), Escape (cancel/back), A (select all), Delete/Backspace (quarantine selected). | **WARNING** |
| 3 | Dark/light appearance specified in R11 but no design tokens or color system mentioned. Implementation should use system appearance detection via Tauri + CSS `prefers-color-scheme`. | OK |
| 4 | The three-pane layout needs a responsive fallback for narrow windows. At minimum: collapse the right inspector pane, show it as a modal or drawer. | OK |
| 5 | Footer status bar described in PRD UX section ("selected copies, bytes, retained originals, and the next action") is a strong pattern. Ensure it updates live during selection, not just on confirm. | OK |

### SELECTIVE EXPANSION: Design for accepted cherry-picks

- D4 drag-and-drop: drop zone visual feedback (highlight border when dragging over the folder cards)
- D5 Quick Look: spacebar on focused thumbnail opens the panel. Keyboard flow: arrow keys to navigate grid, space to preview, escape to close preview.

**Recommendation:** Consider running `/plan-design-review` for a deep design review of this plan before implementation.

**Decision gate:** No user decisions needed. Findings are implementation guidance.

---

## Outside Voice (Native Fallback)

**Provider:** Claude subagent (Codex unavailable: Azure model routing not configured)
**Outside coverage:** unavailable (native fallback does not establish outside coverage)

### Findings and Dispositions

| # | Finding | Severity | Disposition |
|---|---------|----------|-------------|
| OV-1 | No shippable intermediate until Stage 4 -- consider vertical-slice staging | Critical | Implementation guidance for eng review. Staging is PRD input, not a CEO scope decision. D3 already shortens the path. |
| OV-2 | Cross-volume quarantine is a new requirement, not a port of Python behavior | High | Correct relabeling. Plan Section 2 already documents the rescue action. No plan change needed. |
| OV-3 | folder_review.py port complexity undersized (883 lines of tests, 13 functions) | High | Valid sizing concern. Belongs in eng review implementation tasks, not CEO scope. |
| OV-4 | czkawka_core evaluation unnecessary for exact-only MVP -- use walkdir + sha2 + rayon | Medium | Valid. Record as implementation guidance: skip czkawka evaluation for MVP. |
| OV-5 | D8 "annotate REQUIREMENTS.md" is vague | Medium | Clarification: add note to s3.1 and s14 stating pHash deferred per CEO review D3. |
| OV-6 | D5 Quick Look underscoped -- may need Objective-C bridging spike | Medium | D5 is user-approved. Risk was flagged in Section 1. Record: spike needed before committing approach. |
| OV-7 | review_decisions.json import not addressed | Low | Already deferred in PRD: "legacy import is a later reviewed migration." |
| OV-8 | Existing SQLite cache not leveraged for first native scan | Low | Same as OV-7: explicitly deferred in PRD. |

**No approved decisions reopened.** OV-1, OV-3, OV-4 are valid implementation guidance carried to eng review. OV-5 clarifies D8 without changing its scope. OV-6 elevates D5 risk without overriding the user's approval.

Approval readiness: PASS (D1-D8 all approved, outside voice integrated, no unresolved choices)

---

## NOT in scope

### Deferred (to TODOS.md)
- pHash/perceptual matching parity with Python ImageHash (D3: defer to post-MVP)
- Video similarity detection (PRD: after photo parity)
- Audio duplicate detection (PRD: explicitly deferred)
- Windows x64 build and installer (PRD: explicitly deferred)
- Cloud scanning or account-based services (PRD: explicitly deferred)
- Automatic permanent deletion (PRD: explicitly deferred)
- Signed/notarized macOS releases (PRD: unless Apple Developer credentials available)
- Legacy history/cache import from Python app (PRD: later reviewed migration)

### Rejected
- (nothing rejected)

---

## What already exists

| Sub-problem | Existing code | Plan reuses it? |
|---|---|---|
| SHA-256 exact hashing | app.py:42-46, folder_review.py:27-41 | Yes -- golden fixture comparison for Rust port |
| EXIF-corrected RGBA pixel hashing | app.py:49-55 | Yes -- parity tests against Python output |
| Quarantine/restore with collision handling | app.py:200-350 | Yes -- behavior contract ports, journal replaces JSON |
| Folder planning/verification (13 functions) | folder_review.py:44-325 | Yes -- all invariants port; 883 lines of tests as golden reference |
| identity() TOCTOU mitigation | folder_review.py:19-24 | Yes -- O_NOFOLLOW + pre/post checks port directly |
| hash_regular_file() three-stage verify | folder_review.py:27-41 | Yes -- open-check-read-check pattern ports |
| Connected-component grouping | app.py visual grouping logic | Yes -- deterministic keeper ordering ports |
| 64 passing tests | tests/ (304 + 883 lines) | Yes -- golden outputs and parity assertions |
| SQLite scan cache schema | dedupe_cache.sqlite3 (11.8MB) | No -- new schema; legacy import deferred |
| review_decisions.json history | app.py:214-231 | No -- operation journal replaces; import deferred |

---

## Dream state delta

```
CURRENT STATE                    AFTER THIS PLAN                GAP TO 12-MONTH IDEAL
Python/Streamlit app             Tauri 2/React/Rust desktop     pHash parity (deferred D3)
1,254 LOC in app.py              Native .app, cached scans      Video dedup (deferred)
64 tests, works but slow         Exact + pixel dedup            100K+ image handling (needs perf gate)
Web UI, terminal launch          Keyboard-driven review         Signed macOS release (deferred)
30K images = 43s grouping        Target: <500ms cached open     Legacy data import (deferred)
JSON history, SQLite cache       Operation journal + new index  Windows build (deferred)
No git repo                      Git from day 1 (D7)
PNG thumbs in browser            WebP cached thumbnails (D6)
File picker only                 Drag-and-drop + picker (D4)
No native preview                Quick Look integration (D5)
```

The biggest gap to the ideal is pHash parity (D3), intentionally deferred. The plan delivers a complete exact-dedup native app with the safety guarantees, keyboard-driven UX, and performance targets. Video, Windows, and signing are future work.

---

## Error & Rescue Registry (Strategy-Only)

| Capability | Failure mechanism | User impact | Known safeguard | Verification owner |
|---|---|---|---|---|
| Directory walking | Permission denied, symlink loop, disk disconnect | Files skipped; error count shown | Per-file error recording, continue scanning | Implementation: prove skip + count in tests |
| File stat/read | ENOENT (deleted), locked, corrupt | File skipped; cache invalidated | Skip and record; invalidate stale cache entry | Implementation: ENOENT + locked file tests |
| Image decode | Unsupported format, corrupt header | Broken-image icon + tooltip | Store error in index; skip decode | Implementation: corrupt fixture test |
| Image decode (OOM) | 100MP+ image, ~400MB RGBA | **App crash** | **CRITICAL GAP: set max decode dimension** | Implementation: MUST add configurable limit |
| SQLite write | SQLITE_FULL | **Operation fails, unclear error** | **GAP: catch SQLITE_FULL, report "disk full"** | Implementation: MUST handle gracefully |
| SQLite migration | Schema version mismatch | **App won't start** | **GAP: clear error dialog + "reset database" option** | Implementation: MUST show migration error |
| Quarantine move | Cross-volume (st_dev differs) | Transparent to user | Copy-verify-remove workflow (NEW, not ported) | Implementation: design from scratch per OV-2 |
| Quarantine move | Destination collision | Shows new suffixed path | Suffix-based rename | Implementation: collision tests exist in Python |
| Quarantine verify | File changed during verify | "File changed, refresh required" | Abort operation, preserve source | Implementation: identity check tests |
| Journal recovery | Crash between PENDING and COMPLETED | Automatic reconciliation on restart | Journal state machine + startup reconciliation | Implementation: fault injection tests |
| Restore | Original path occupied, parent missing | Suffix rename or create parent | Collision-safe restore | Implementation: restore edge case tests |
| Thumbnail generation | Decoder failure, cache dir full | Placeholder shown | Skip + broken-image fallback | Implementation: fallback test |
| Tauri IPC | Serialization failure, worker panic | Toast with error details | Tauri error handler catches panics | Implementation: error propagation test |

---

## Failure Modes Registry

| Capability | Failure mode | Rescued? | Test? | User sees? | Logged? |
|---|---|---|---|---|---|
| Image decode | OOM on 100MP+ image | N | N | App crash | N |
| SQLite | Disk full (SQLITE_FULL) | N | N | Silent failure | N |
| SQLite | Migration failure | N | N | App won't start | N |
| Scanner | Permission denied | Y | Y (Python) | "N files skipped" | Y |
| Scanner | File deleted mid-scan | Y | Y (Python) | File disappears | Y |
| Hasher | File changed during read | Y | Y (Python) | "File changed" | Y |
| Image decode | Unsupported format | Y | Y (Python) | Broken icon | Y |
| Quarantine | Cross-volume move | Y (spec) | N | Transparent | Y |
| Quarantine | Destination collision | Y | Y (Python) | New path shown | Y |
| Quarantine | Source disappeared | Y | Y (Python) | Per-file error | Y |
| Restore | Path occupied | Y | Y (Python) | Suffix rename | Y |
| Journal | Crash recovery | Y (spec) | N | Auto-reconcile | Y |
| Thumbnail | Decode failure | Y (spec) | N | Placeholder | Y |
| Quick Look (D5) | Unsupported file | Y | N | QL "no preview" | N |
| Rapid confirm | Double-click quarantine | N (spec) | N | **Duplicate action** | N |

**3 CRITICAL GAPS** (Rescued=N, Test=N, User Sees=crash/silent): OOM, disk full, migration failure.
**4 unrescued in spec** needing implementation proof: cross-volume, journal recovery, thumbnail fallback, rapid confirm.

---

## Scope Expansion Decisions

### Accepted (6)
- D2: 2-3 crates instead of 6 (effort S)
- D3: Defer pHash to post-MVP (effort S)
- D4: Drag-and-drop folder selection (effort S)
- D5: Quick Look integration (effort M -- elevated risk per OV-6, spike recommended)
- D6: WebP thumbnail cache (effort S)
- D7: Git init before implementation (effort S)

### Deferred (1)
- pHash parity with Python ImageHash -- to TODOS.md, post-MVP

### Skipped (0)
- (nothing rejected)

---

## Diagrams

### 1. System Architecture
(See Section 1 above -- full ASCII diagram of Tauri app + core + index crates)

### 2. Data Flow
(See Section 1 above -- exact dedup scan and quarantine flows with happy/nil/empty/error paths)

### 3. State Machine (Operation Journal)

```
                    +----------+
                    | PENDING  |
                    +----+-----+
                         |
            +------------+------------+
            |            |            |
     rename succeeds  rename fails  crash
            |            |            |
    +-------v-----+ +---v------+ +---v---------+
    | COMPLETED   | | FAILED   | | (no record) |
    +-------------+ +----------+ +------+------+
                                        |
                                  startup reconciliation
                                        |
                         +--------------+--------------+
                         |              |              |
                   source exists   dest only     both exist
                         |              |              |
                  +------v------+ +----v-------+ +---v--------+
                  | ROLLED_BACK | | COMPLETED  | | verify dest|
                  +-------------+ +------------+ +---+--------+
                                                     |
                                              match: COMPLETED
                                           no match: alert user
```

### 4. Error Flow

```
Any operation
    |
    v
try { operation }
    |
    +-- IO error --> record in index --> skip file --> continue scan
    |
    +-- FileChanged --> abort batch --> preserve all sources --> show error
    |
    +-- CrossVolume --> copy-verify-remove workflow
    |                      |
    |                      +-- verify fails --> remove dest, preserve source
    |
    +-- Collision --> suffix rename --> continue
    |
    +-- OOM (CRITICAL GAP) --> process crash --> NO RESCUE
    |
    +-- SQLITE_FULL (GAP) --> operation fails --> unclear error
```

### 5. Deployment Sequence

```
Stage 1: git init -> cargo init (core + index) -> golden fixtures -> parity tests
Stage 2: scanner + size filter + prehash + full hash -> SQLite cache -> benchmarks
Stage 3: tauri init -> React scaffold -> folder nav + contact sheet + Quick Look
Stage 4: quarantine journal + move/restore + confirmation UI -> cleanup workflow
Stage 5: (deferred) pHash port + BK-tree + perceptual grouping
Stage 6: DMG packaging -> smoke tests -> accessibility audit -> release
```

### 6. Rollback Flowchart

```
Native app broken?
    |
    +-- Yes --> Uninstall .app (drag to trash)
    |              |
    |              v
    |           Python app still works (preserved by design)
    |              |
    |              v
    |           source .venv/bin/activate && streamlit run app.py
    |              |
    |              v
    |           Rollback time: seconds
    |
    +-- Quarantine data in native journal?
           |
           +-- Yes --> Journal has full operation log
           |           Manual restore possible via journal query
           |
           +-- No --> Nothing lost; Python app has its own history
```

### Stale Diagram Audit

No ASCII diagrams exist in the current codebase files (app.py, folder_review.py, tests/). The PRD and REQUIREMENTS.md contain no diagrams. No stale diagrams found.

---

## Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific finding above. Run with Claude Code or Codex; checkbox as you ship.

- [ ] **T1 (P1, human: ~4h / CC: ~15min)** -- core -- Set max image decode dimension to prevent OOM
  - Surfaced by: Section 2 -- CRITICAL GAP: OOM on 100MP+ images, ~400MB RGBA decode
  - Files: to be determined (new Rust core crate)
  - Verify: Test with synthetic image claiming 100MP dimensions; verify skip + error recording

- [ ] **T2 (P1, human: ~2h / CC: ~10min)** -- index -- Handle SQLITE_FULL gracefully
  - Surfaced by: Section 2 -- WARNING: no rescue for disk-full SQLite writes
  - Files: to be determined (new Rust index crate)
  - Verify: Fill disk (or mock), trigger write, verify user-visible "disk full" message

- [ ] **T3 (P1, human: ~2h / CC: ~10min)** -- index -- Show clear error on schema migration failure
  - Surfaced by: Section 2 -- WARNING: app won't start on migration failure
  - Files: to be determined (new Rust index crate)
  - Verify: Corrupt schema version, launch app, verify error dialog with "reset database" option

- [ ] **T4 (P2, human: ~1h / CC: ~5min)** -- app -- Disable quarantine confirm button after first click
  - Surfaced by: Section 4 -- WARNING: rapid double-click on quarantine action
  - Files: to be determined (React frontend)
  - Verify: Click confirm rapidly; verify only one operation executes

- [ ] **T5 (P2, human: ~30min / CC: ~5min)** -- docs -- Fix Node version in PRD (25.9.0 -> 24.22.1)
  - Surfaced by: Section 5 / Reality Rows -- PRD.md:113 claims wrong Node version
  - Files: documentation/stories/native-desktop/PRD.md
  - Verify: Check `node --version` matches PRD

- [ ] **T6 (P2, human: ~1h / CC: ~5min)** -- docs -- Annotate REQUIREMENTS.md for D3/D8 pHash deferral
  - Surfaced by: Outside Voice OV-5 / D8 -- "annotate" is vague
  - Files: REQUIREMENTS.md (s3.1 and s14)
  - Verify: Read s3.1 and s14; confirm pHash is marked as deferred with CEO review reference

- [ ] **T7 (P2, human: ~2h / CC: ~10min)** -- core -- Design cross-volume copy-verify-remove from scratch
  - Surfaced by: Outside Voice OV-2 -- this is a new requirement, not a Python port
  - Files: to be determined (new Rust core crate)
  - Verify: Test with files on different volumes; verify atomic-safe copy+verify+remove

- [ ] **T8 (P2, human: ~4h / CC: ~15min)** -- build -- Add cargo audit to Stage 6 exit evidence
  - Surfaced by: Section 3 -- WARNING: no dependency vulnerability scanning
  - Files: to be determined (CI or pre-release script)
  - Verify: Run `cargo audit`; verify it reports and blocks on known vulnerabilities

- [ ] **T9 (P2, human: ~1h / CC: ~5min)** -- app -- Specify Tauri capability scoping (scoped fs permissions)
  - Surfaced by: Section 3 -- WARNING: Tauri capabilities not specified
  - Files: to be determined (src-tauri/capabilities/)
  - Verify: Confirm app uses `fs:allow-read` and `fs:allow-write` with folder scoping, not blanket

- [ ] **T10 (P3, human: ~2h / CC: ~10min)** -- app -- Spike D5 Quick Look feasibility
  - Surfaced by: Outside Voice OV-6 -- Objective-C bridging complexity unknown
  - Files: to be determined (proof-of-concept)
  - Verify: Demonstrate QLPreviewPanel opening from a Tauri 2 app, or document why fallback is needed

- [ ] **T11 (P3, human: ~1h / CC: ~5min)** -- core -- Add configurable I/O concurrency for external storage
  - Surfaced by: Section 7 -- WARNING: bounded workers need configurable limit
  - Files: to be determined (new Rust core crate)
  - Verify: Set concurrency=1, scan external drive, verify single-threaded I/O

- [ ] **T12 (P3, human: ~30min / CC: ~5min)** -- app -- Specify max log file size
  - Surfaced by: Section 8 -- WARNING: no log rotation specified
  - Files: to be determined (tracing-appender config)
  - Verify: Verify log file does not exceed 10MB cap

- [ ] **T13 (P3, human: ~2h / CC: ~10min)** -- build -- Add scripted smoke test for packaged .app
  - Surfaced by: Section 9 -- WARNING: no automated smoke test
  - Files: to be determined (test script)
  - Verify: Smoke test launches .app, scans fixture folder, verifies result count, exits

_No new tasks from Section 10 (Future)._

---

## Completion Summary

```
  +====================================================================+
  |            MEGA PLAN REVIEW -- COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | 2,766 LOC, 64 tests, no git repo, no prior |
  |                      | reviews, Node version wrong in PRD          |
  | Step 0               | SELECTIVE EXPANSION + 8 decisions (D1-D8)   |
  | Section 1  (Arch)    | 4 findings (1 WARNING, 3 OK)                |
  | Section 2  (Errors)  | 13 error paths mapped, 3 GAPS (1 CRITICAL) |
  | Section 3  (Security)| 7 threats, 2 WARNINGs                      |
  | Section 4  (Data/UX) | 11 edge cases mapped, 3 WARNINGs            |
  | Section 5  (Quality) | 1 WARNING (Node version)                    |
  | Section 6  (Tests)   | Diagram produced, 2 WARNINGs                |
  | Section 7  (Perf)    | 2 WARNINGs (concurrent decode, ext storage) |
  | Section 8  (Observ)  | 1 WARNING (log rotation)                    |
  | Section 9  (Deploy)  | 1 WARNING (smoke test)                      |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 2           |
  | Section 11 (Design)  | 2 WARNINGs (empty state, keyboard shortcuts)|
  +--------------------------------------------------------------------+
  | NOT in scope         | written (8 deferred, 0 rejected)            |
  | What already exists  | written (10 items, 8 reused)                |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 14 rows, 1 CRITICAL GAP                    |
  | Failure modes        | 15 total, 3 CRITICAL GAPS                   |
  | TODOS.md updates     | 0 new proposals (all resolved in D1-D8)     |
  | Scope proposals      | 6 proposed, 6 accepted, 1 deferred          |
  | CEO plan             | written                                     |
  | Outside voice        | Claude subagent / unavailable (Codex model  |
  |                      | routing not configured). 8 findings, 0      |
  |                      | decisions reopened, valid impl guidance.     |
  | Lake Score           | N/A (no coverage-scored questions)           |
  | Diagrams produced    | 6 (architecture, data flow, state machine,  |
  |                      | error flow, deployment sequence, rollback)   |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 1 unverified       |
  +====================================================================+
```

### Unresolved Decisions

None. All 8 decisions (D1-D8) are approved.

## Design Review

**Skill:** /gstack-plan-design-review
**Date:** 2026-10-23
**Initial design score:** 5/10
**User priorities:** UX-rich, simple navigation, extensible for video/other file types, system-wide search

### Design Decision Ledger

| ID | Question | Choice | Rationale |
|---|---|---|---|
| DD1 | Focus areas | Weight search + nav + keys | User's stated priorities map to the biggest gaps |
| DD2 | Search UX | Persistent header search bar | macOS convention (Finder, Photos); filters contact sheet in place; extends to video/other types |
| DD3 | Media type navigation | Top-level tab bar (Photos \| Videos \| All) | Adding a type = adding a tab; matches Apple Photos segmented control; tab bar appears when video ships |
| DD4 | First-run and empty states | Drop zone + inline empty states | Full-screen drop zone on first run; zero-dupes shows "No duplicates in N files. Try another folder?" |
| DD5 | Post-cleanup reinforcement | Summary banner | "Moved N files (X.X GB). Undo available in Quarantine." Auto-dismiss 5s |
| DD6 | Design system baseline | macOS-native feel | System font (-apple-system/SF Pro), system colors, platform-like controls; dark/light automatic |
| DD7 | Keyboard shortcuts | Full map specified | Every binding follows macOS convention; covers full review workflow |
| DD8 | Thumbnail density | ~160px with zoom slider | Matches Apple Photos; slider in footer status bar lets users adjust |

### Updated Information Architecture

```
+------------------------------------------------------------------+
|                    Tauri Desktop App                               |
|  +--------------------------------------------------------------+ |
|  | [App Icon] [Search: _______________] [Photos | Videos | All] | |
|  +--------------------------------------------------------------+ |
|  | +----------+ +---------------------+ +---------------------+ | |
|  | | Folder   | | Contact Sheet       | | Comparison          | | |
|  | | Nav      | | (~160px thumbnails  | | Inspector           | | |
|  | |          | |  with zoom slider)  | | (or Quick Look)     | | |
|  | | Scanned  | |                     | |                     | | |
|  | | folders  | | [keeper] [copy]     | | Side-by-side        | | |
|  | | ranked   | | [copy]  [copy]      | | metadata + preview  | | |
|  | | by bytes | |                     | |                     | | |
|  | | reclaimb | | Group 2:            | | Collapse to drawer  | | |
|  | |          | | [keeper] [copy]     | | at <900px width     | | |
|  | +----------+ +---------------------+ +---------------------+ | |
|  +--------------------------------------------------------------+ |
|  | Status: 3 selected | 145 MB | Quarantine | [zoom ---+--- ]   | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

First run (no folders loaded):
```
+------------------------------------------------------------------+
|  [Search: _______________]                    [Photos]            |
|                                                                   |
|                                                                   |
|              +---------------------------+                        |
|              |                           |                        |
|              |   Drop a folder here      |                        |
|              |   or click to browse      |                        |
|              |                           |                        |
|              |      [ Browse... ]        |                        |
|              |                           |                        |
|              +---------------------------+                        |
|                                                                   |
+------------------------------------------------------------------+
```

### Keyboard Shortcut Map

| Key | Action | Context |
|---|---|---|
| Arrow keys | Navigate thumbnail grid | Contact sheet focused |
| Space | Quick Look preview (D5) | Thumbnail selected |
| Return | Confirm current action | Dialog or selection |
| Delete / Backspace | Quarantine selected copies | Copies selected |
| Cmd+A | Select all copies in group | Contact sheet focused |
| Cmd+Z | Undo last quarantine batch | Global |
| Tab | Cycle focus: folder nav -> contact sheet -> inspector | Global |
| Escape | Close inspector / cancel dialog / clear search | Context-dependent |
| Cmd+F | Focus search bar (DD2) | Global |
| Cmd+1/2/3 | Switch media type tab (DD3) | Global (when tabs visible) |
| Cmd+Plus/Minus | Zoom thumbnails in/out (DD8) | Contact sheet focused |

### User Journey Storyboard

```
STEP | USER DOES                    | USER FEELS           | PLAN SPECIFIES
-----|------------------------------|----------------------|------------------
1    | Opens app (first time)       | Curious, cautious    | DD4: full-screen drop zone
2    | Drops a folder               | Committed, hopeful   | CEO D4: drag-and-drop
3    | Watches scan progress        | Anxious: "how long?" | Progress bar, phase, cancel
4    | Sees folder overview         | Surprised: "that many?" | Ranked folders, bytes reclaimable
5    | Browses duplicate groups     | In control, deciding | Contact sheet, keeper marked
6    | Previews with Quick Look     | Confident: "yes same"| CEO D5: spacebar preview
7    | Searches for a specific file | Purposeful           | DD2: header search bar
8    | Selects copies to quarantine | Cautious: "am I sure?"| Confirm dialog, counts, guard
9    | Sees quarantine complete     | Relieved, satisfied  | DD5: summary banner "freed 2.3 GB"
10   | Checks quarantine list       | Reassured: "I can undo"| Restore available
```

### Interaction State Updates (from design review)

| Feature | Loading | Empty | Error | Success | Partial |
|---|---|---|---|---|---|
| First run | N/A | DD4: drop zone, "Drop a folder or click to browse" | N/A | Transitions to scan | N/A |
| Search (DD2) | Live filter as you type | "No matches for [query]" + clear button | N/A | Contact sheet filtered | Partial matches shown |
| Media tabs (DD3) | N/A | "No [type] duplicates. Scan a folder with [type] files." | N/A | Tab shows filtered groups | N/A |
| Post-quarantine | N/A | N/A | N/A | DD5: banner "Moved N files (X.X GB)" | Partial: "Moved N of M. K failed." |
| Zero duplicates | N/A | DD4: "No duplicates in N files. Try another folder?" | N/A | N/A | N/A |

### Responsive Behavior

- **>= 1200px:** Full three-pane layout (folder nav + contact sheet + inspector)
- **900-1199px:** Two-pane (folder nav + contact sheet). Inspector opens as a slide-over drawer from right.
- **< 900px:** Single pane. Folder nav in a collapsible sidebar. Inspector as full-screen overlay.
- Window resize is live; panes adjust without reload.

### Accessibility Baseline

- ARIA landmarks: `navigation` (folder nav), `main` (contact sheet), `complementary` (inspector)
- Visible focus ring on all interactive elements (system focus ring via DD6)
- Alt text on thumbnails: filename + dimensions + file size
- Color contrast: system colors (DD6) meet WCAG AA automatically in both modes
- Screen reader: group counts, selection state, and action results announced via live regions

### Design Review Implementation Tasks

- [ ] **T14 (P1, human: ~4h / CC: ~15min)** -- app -- Implement persistent header search bar (DD2)
  - Surfaced by: Pass 1 -- no search in information architecture
  - Files: React frontend (header component, contact sheet filter logic)
  - Verify: Type filename -> contact sheet filters in place; clear -> restores full view

- [ ] **T15 (P2, human: ~2h / CC: ~10min)** -- app -- Add media type tab bar infrastructure (DD3)
  - Surfaced by: Pass 1 -- no media type navigation model
  - Files: React frontend (tab bar component, routing)
  - Verify: MVP shows "Photos" tab only; tab bar structure ready for video tab addition

- [ ] **T16 (P1, human: ~2h / CC: ~10min)** -- app -- Build first-run drop zone and empty states (DD4)
  - Surfaced by: Pass 2 -- no first-run state
  - Files: React frontend (welcome screen, empty state components)
  - Verify: Fresh install shows drop zone; scan with zero dupes shows confirmation message

- [ ] **T17 (P2, human: ~1h / CC: ~5min)** -- app -- Add post-quarantine summary banner (DD5)
  - Surfaced by: Pass 3 -- no post-cleanup reinforcement
  - Files: React frontend (banner component, quarantine result handler)
  - Verify: Quarantine 3 files -> banner shows count + size + undo link; auto-dismisses

- [ ] **T18 (P2, human: ~2h / CC: ~10min)** -- app -- Implement full keyboard shortcut map (DD7)
  - Surfaced by: Pass 6 -- keyboard shortcuts not enumerated
  - Files: React frontend (keyboard handler, focus management)
  - Verify: Arrow keys navigate grid, Space opens Quick Look, Cmd+F focuses search, Tab cycles panes

- [ ] **T19 (P2, human: ~1h / CC: ~5min)** -- app -- Add thumbnail zoom slider to footer (DD8)
  - Surfaced by: Pass 7 -- thumbnail density unspecified
  - Files: React frontend (footer status bar, contact sheet grid)
  - Verify: Slider adjusts thumbnail size from ~100px to ~300px; default ~160px

- [ ] **T20 (P3, human: ~3h / CC: ~15min)** -- app -- Implement responsive three-pane to single-pane
  - Surfaced by: Pass 6 -- narrow window behavior unspecified
  - Files: React frontend (layout components, CSS breakpoints)
  - Verify: Resize window below 900px -> inspector becomes drawer; below 900px -> single pane

_No new tasks from Pass 4 (AI Slop) or Pass 5 (Design System -- DD6 is a direction, not a build task)._

### NOT in scope (design review)

- Full DESIGN.md with token specifications -- deferred to `/design-consultation`
- Custom app icon and branding -- utility app, system icon sufficient for MVP
- Onboarding wizard or feature tour -- DD4 drop zone is sufficient
- Animation/transition specifications -- system defaults via DD6
- Touch/tablet support -- desktop-only app

### What already exists (design review)

- CEO review Section 11: three-pane layout, user flow, interaction state table (7 features x 5 states)
- CEO review Section 4: quarantine and scan data flows with happy/nil/empty/error paths
- REQUIREMENTS.md s7: navigation sections, scan screen, duplicate review, quarantine review specs
- docs/ux-roadmap.md: folder-level review, ranked overview, contact sheet, keyboard shortcuts, recovery
- Python app behavioral patterns: two-folder comparison, thumbnail grid, quarantine list, stats display

### TODOS.md updates (design review)

1. **DESIGN.md creation via /design-consultation** -- macOS-native token set with system font, system colors, spacing scale, component vocabulary. **Why:** DD6 sets the direction but implementation needs concrete tokens. **Depends on:** nothing; can run any time before Stage 3 UI work.

## Design Review Completion Summary

```
  +====================================================================+
  |         DESIGN PLAN REVIEW -- COMPLETION SUMMARY                    |
  +====================================================================+
  | System Audit         | No DESIGN.md, Streamlit UI only, no prior   |
  |                      | design reviews                               |
  | Step 0               | 5/10 initial, focus: search+nav+keys         |
  | Pass 1  (Info Arch)  | 6/10 -> 8/10 after fixes (DD2 search, DD3   |
  |                      | media tabs)                                   |
  | Pass 2  (States)     | 6/10 -> 8/10 after fixes (DD4 first-run,    |
  |                      | search states, zero-dupes empty state)        |
  | Pass 3  (Journey)    | 5/10 -> 8/10 after fixes (storyboard, DD5   |
  |                      | post-cleanup banner)                          |
  | Pass 4  (AI Slop)    | 8/10 -> 8/10 (OPERATE classifier, no slop   |
  |                      | patterns, native three-pane layout)           |
  | Pass 5  (Design Sys) | 3/10 -> 7/10 after fixes (DD6 macOS-native  |
  |                      | baseline; full DESIGN.md deferred to TODO)    |
  | Pass 6  (Responsive) | 4/10 -> 8/10 after fixes (DD7 keyboard map, |
  |                      | responsive breakpoints, a11y baseline)        |
  | Pass 7  (Decisions)  | 7 resolved, 0 deferred                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (5 items)                            |
  | What already exists  | written                                      |
  | TODOS.md updates     | 1 item (DESIGN.md via /design-consultation)  |
  | Approved Mockups     | 0 (designer not available)                   |
  | Decisions made       | 7 added to plan (DD2-DD8)                    |
  | Decisions deferred   | 0                                            |
  | Overall design score | 3/10 -> 7/10                                 |
  +====================================================================+
```

Pass 5 at 7/10 keeps the overall below 8. The gap: no concrete DESIGN.md with tokens. DD6 locks the direction (macOS-native) but the implementer still needs a token file to build from. Run `/design-consultation` before Stage 3 UI work to close this.

### Unresolved Decisions

None. All 7 design decisions (DD2-DD8) are approved.

## Engineering Review

**Skill:** /gstack-plan-eng-review
**Date:** 2026-10-23
**Session:** 53255-1792746460-e02fe5e8
**Target:** docs/designs/native-desktop-ceo-review.md (plan mode, auto-selected)
**Search:** unavailable -- proceeding with in-distribution knowledge only

### Reality Rows (Eng Review)

REALITY: premise-table pass unverified=1 (Node version wrong, carried from CEO) PRD.md:113
REALITY: already-done pass No prior implementation commits PRD.md:3
REALITY: surface-check pass No CLI commands in plan to verify (spec, not diff) REQUIREMENTS.md:1
REALITY: binding-decisions pass CEO D1-D8 and Design DD2-DD8 are binding docs/designs/native-desktop-ceo-review.md:126-137
REALITY: numbers finding Node version wrong (25.9.0 vs 24.22.1); perf targets estimated PRD.md:113
REALITY: deferred-asks pass pHash (D3), video, audio, Windows, cloud, auto-delete all explicitly deferred docs/designs/native-desktop-ceo-review.md:148-156
REALITY: pr-count pass No git repo yet; D7 approves git init; staged delivery implies 4-6 PRs per stage docs/designs/native-desktop-ceo-review.md:136

### Scope Challenge

**A. Assess the target**

**What already solves each sub-problem?** All identified in CEO 0B. Python reference covers hashing, grouping, quarantine, and 64 tests as golden fixtures. No additional reusable code found.

**Minimum changes:** Rust core (exact hash + pixel hash) + SQLite index + Tauri shell + React frontend + quarantine journal. D3 (defer pHash) already removes the hardest parity problem.

**Complexity check:**
- Proposed new modules: core crate, index crate, Tauri app, React frontend = 4 modules
- New services: scanner, hasher, pixel_hasher, grouper, quarantine engine, journal, IPC commands = 7+ services
- Exceeds 8 files AND 2 new classes/services. Complexity gate trips.

**TODOS cross-reference:** No TODOS.md exists. Plan proposes items in "Deferred to TODOS.md" section.

**Distribution check:** macOS DMG in Stage 6. Unsigned unless Apple Developer credentials. No CI/CD pipeline for automated builds.

**B. Resolve complexity selectors**

Gate trips (4 modules, 7+ services). Structure question resolved by exact prior approval: CEO D2 approved "2-3 crates, split when needed" (user choice via D2). No feature cuts proposed. Structure: core + index + Tauri app, matching D2.

Scope record: feature answers: D2 (2-3 crates); structure: D2-approved (core + index + app); accepted scope: all CEO and design scope preserved; pending remedies: none.

**C. Resolve findings**

Scope Challenge result: **scope accepted as-is** (D2 covers structure, no cuts).

---

### Section 1: Architecture Review

The CEO review's architecture analysis (Sections 1, 4) is thorough. Eng review focuses on gaps:

| # | Finding | Severity | Confidence |
|---|---------|----------|------------|
| E1 | **Missing Tauri IPC command inventory.** Plan says "commands/ -> delegates to core + index" but never lists the commands. Minimum needed: `scan_folders`, `cancel_scan`, `get_groups`, `get_thumbnail`, `quarantine_files`, `restore_files`, `delete_quarantined`, `open_quick_look`. Without this, frontend and backend designs diverge at the IPC boundary. | WARNING | 8/10 |
| E2 | **Missing event stream specification.** Plan mentions "Tauri event streams progress" without naming event types. Need: `scan:progress`, `scan:complete`, `scan:error`, `scan:cancelled` at minimum. Standard Tauri pattern, not blocking. | OK | 9/10 |
| E3 | **No frontend state management specified.** Three-pane layout with scan progress, group selection, quarantine state, and search filtering needs a state strategy. React Context, Zustand, or Tauri store. Affects responsiveness during long scans. | OK | 7/10 |

Dispositions: E1-E3 are implementation guidance. No user decisions needed.

---

### Section 2: Code Quality Review

Plan review (no code exists). Evaluating spec quality:

| # | Finding | Severity | Confidence |
|---|---------|----------|------------|
| E4 | **REQUIREMENTS.md s4 still proposes 6 crates; D2 approved 2-3.** D8 authorized updating REQUIREMENTS.md but T6 hasn't been done. A new contributor reading REQUIREMENTS.md would build the wrong structure. Already tracked in T6; promote T6 to P1. | OK | 10/10 |
| E5 | **Pixel hash serialization format unspecified.** `app.py:48-55` uses width+height as big-endian 8-byte prefixes before raw RGBA bytes. This exact byte format is the parity contract. Plan says "parity tests" but doesn't specify what to match. The golden fixtures will catch it, but an implementer reading only the plan won't know to look for the dimension prefix. | WARNING | 9/10 |

Dispositions: E4 already tracked (T6, promoted to P1). E5 is a new documentation requirement.

---

### Section 3: Test Review

**Test framework:** CLAUDE.md says "No automated testing framework." For the Rust project: `cargo test`. Frontend framework unresolved (decide at Stage 3).

**Coverage Diagram**

```
CODE PATHS                                              USER FLOWS
[PLANNED] crate: core                                   [PLANNED] Scan workflow
  |- scanner::walk()                                      |- [GAP] Select via drag-and-drop (DD4)
  |   |- [GOLDEN] happy path -- parity with Python        |- [GAP] Two-folder asymmetric selection (OV-1)
  |   |- [GAP] Permission denied skip + count             |- [GAP] Start scan + progress
  |   |- [GAP] Symlink loop rejection                     |- [GAP] Cancel mid-scan
  |   '- [GAP] Disk disconnect mid-walk                   '- [GAP] Resume from cache
  |- hasher::prehash()                                  
  |   |- [GOLDEN] 4KB prefix -> full when unique         [PLANNED] Review workflow
  |   |- [GAP] File < 4KB                                 |- [GAP] Navigate grid (DD7 keyboard)
  |   '- [GAP] File changed during read                   |- [GAP] Search filter (DD2)
  |- hasher::full_hash()                                   |- [GAP] Quick Look preview (DD5)
  |   |- [GOLDEN] SHA-256 parity                           |- [GAP] Select copies for quarantine
  |   '- [GAP] Large file streaming                        '- [GAP] Confirm with count/size
  |- pixel_hasher::normalize()                          
  |   |- [GOLDEN] EXIF transpose parity                  [PLANNED] Quarantine workflow
  |   |- [GOLDEN] RGBA convert parity                      |- [GAP] [->E2E] Move -> verify -> update
  |   |- [GAP] Grayscale input                             |- [GAP] Cross-volume quarantine
  |   |- [GAP] Unsupported format error                    |- [GAP] [->E2E] Restore to occupied path
  |   '- [GAP] OOM on 100MP+ (T1)                         |- [GAP] Confirm permanent delete
  |- grouper::build_groups()                               '- [GAP] [->E2E] Undo last batch (Cmd+Z)
  |   |- [GOLDEN] Hash-equality grouping                
  |   |- [GOLDEN] Keeper ordering                        [PLANNED] Edge cases
  |   '- [GAP] Group overlap: exact vs pixel-identical     |- [GAP] Empty folder scan
  |- quarantine::verify_plan()                             |- [GAP] Zero duplicates (DD4)
  |   |- [GAP] File changed during verify                  |- [GAP] [->E2E] Rapid double-click (T4)
  |   |- [GAP] File missing                                |- [GAP] Window resize <900px (T20)
  |   '- [GAP] Keeper in selection                         '- [GAP] First-run state (DD4)
  |- quarantine::execute()                              
  |   |- [GAP] Same-volume rename                       
  |   |- [GAP] Cross-volume copy-verify-remove (T7)     
  |   |- [GAP] Permission denied                        
  |   '- [GAP] Collision -> suffix rename               
  '- restore::execute()                                 
      |- [GAP] Quarantine file missing                  
      |- [GAP] Original path occupied                   
      '- [GAP] Parent dir missing                       

[PLANNED] crate: index                                   
  |- cache operations                                    
  |   |- [GAP] Insert/update                             
  |   |- [GAP] SQLITE_FULL (T2)                         
  |   '- [GAP] Cache hit/miss/stale                     
  |- migration::run()                                    
  |   '- [GAP] Failed migration (T3)                    
  '- journal::write()                                    
      '- [GAP] Crash recovery state machine             

COVERAGE: 6/38 code paths have golden references (16%)  |  0/38 tested (0% -- greenfield)
USER FLOWS: 0/16 tested  |  3 recommended [->E2E]
QUALITY: no tests exist  |  GAPS: 38 code + 16 user = 54 total (expected for greenfield plan)
```

**Critical regression requirements (golden fixture parity):**

1. **Exact hash parity:** Python `folder_review.py:27-41` -> Rust `core::hasher::full_hash`
   Value: protects=SHA-256 hash consistency; fails_when=hashing diverges; why_new=greenfield Rust; seam=none; no_claim=none

2. **Pixel hash parity:** Python `app.py:48-55` -> Rust `core::pixel_hasher::normalize` (dimension prefix + RGBA bytes)
   Value: protects=EXIF-transpose+RGBA fingerprint; fails_when=normalization pipeline changes; why_new=greenfield Rust; seam=none; no_claim=none

3. **Keeper ordering parity:** Python keeper logic -> Rust `core::grouper::keeper_order`
   Value: protects=deterministic keeper selection; fails_when=sort priority changes; why_new=greenfield Rust; seam=none; no_claim=none

4. **Quarantine safety:** `folder_review.py:identity()` pattern -> Rust equivalent
   Value: protects=pre/post identity checks; fails_when=check removed/reordered; why_new=new implementation; seam=none; no_claim=concurrent attacker

| # | Finding | Severity | Confidence |
|---|---------|----------|------------|
| E6 | **Group overlap between exact and pixel-identical unspecified.** Byte-identical files also match pixel-identical (same pixel hash). Plan doesn't say whether to deduplicate across categories. Users could see the same group in both views and double-quarantine. | WARNING | 8/10 |
| E7 | **No frontend test framework chosen.** `cargo test` for Rust is implicit. Frontend (React component tests, E2E) needs a framework decision at Stage 3. Not blocking plan approval. | OK | 9/10 |

Dispositions: E6 needs specification before Stage 3 UI. E7 deferred to Stage 3.

---

### Section 4: Performance Review

CEO Section 7 was thorough. Eng review additions:

| # | Finding | Severity | Confidence |
|---|---------|----------|------------|
| E8 | **Concurrent image decode limit undefined.** CEO flagged ~384MB with 4 concurrent (WARNING). With rayon default (8-10 cores), peak is ~768-960MB for 24MP images. Need a separate decode semaphore (2-4 concurrent), not the general rayon pool. | WARNING | 8/10 |
| E9 | **SQLite WAL mode not explicitly required.** Plan mentions WAL for SQLITE_FULL handling but doesn't specify it as an index crate requirement. WAL is needed for concurrent reads during scan (UI reads groups while scanner writes). Add `PRAGMA journal_mode=WAL` to index crate init. | WARNING | 9/10 |

Dispositions: E8 extends CEO finding #4 with a specific limit. E9 is a new implementation requirement.

---

### Outside Voice (Native Fallback)

**Provider:** Claude subagent (Codex unavailable: Azure model routing not configured for frontier plan-review model)
**Outside coverage:** unavailable (native fallback does not establish outside coverage)

OUTSIDE VOICE (Claude subagent):

| # | Finding | Severity | Disposition |
|---|---------|----------|-------------|
| OV-1 | **Two-folder asymmetric comparison model unspecified in port UI.** The Python app's core interaction is original vs. duplicate folders with keeper protection. The plan's UI describes generic "folder selection" without the two-role semantics. `validate_duplicate_scope()` at `folder_review.py:111-126` enforces distinct, non-overlapping roots. If the Rust port implements naive "scan folders," keeper protection breaks. | **High** | Valid. Add task T21 to specify two-folder model in port UI. P1. |
| OV-2 | **Cross-volume quarantine mischaracterized as new.** `shutil.move()` already handles cross-volume via copy+delete. The Rust port adds hash verification on top, but the mechanism isn't new. CEO OV-2 overstated the novelty. | Medium | Valid correction. T7 description updated: port + extend, not design from scratch. |
| OV-3 | **Pixel hash serialization format unspecified.** `app.py:48-55` uses width+height as big-endian 8-byte prefixes before raw RGBA bytes. Plan says "parity tests" without specifying what to match. | Medium | Valid. Covered in E5. Add to golden fixture spec. |
| OV-4 | **BK-tree insertion order affects group determinism.** Self-corrected to Low: only relevant post-MVP when pHash is added. | Low | Noted for post-MVP. No action now. |
| OV-5 | **Python's non-atomic move-then-log gap not documented.** `app.py:339-380` moves files then writes history. If crash between move and log, no recovery record. The Rust journal fixes this. Golden tests must test correct journal semantics, not replicate the Python bug. | Medium | Valid. Implementation guidance for golden test design. |
| OV-6 | **Exact and pixel-identical group overlap unspecified.** Byte-identical files also match pixel-identical. Plan doesn't say whether to deduplicate. | Medium | Valid. Same as E6. Needs specification before Stage 3 UI. |
| OV-7 | **20 tasks with no stage mapping or dependency graph.** Tasks numbered by priority but not mapped to stages. Implementer can't determine order. | **High** | Valid. Add task-to-stage mapping below. |
| OV-8 | **review_decisions.json format undocumented for transition.** If user quarantines with Python app then installs native, no recovery record in new journal. | Low | Already deferred in plan: "legacy import is a later reviewed migration." |
| OV-9 | **T6 (annotate REQUIREMENTS.md) should be P0/P1, not P2.** Until done, spec and plan disagree. | Low | Valid. Promoted T6 to P1. |
| OV-10 | **Tauri vs SwiftUI trade-off never evaluated.** SwiftUI gets Quick Look and drag-and-drop for free. Tauri chosen for Windows portability. | Medium | Architecture choice is settled in the PRD. Tauri preserves the Windows portability goal (s3.3). D4 and D5 are accepted additions, not compensations. Not reopening. |

**No approved decisions reopened.** OV-1 and OV-7 are valid high-priority additions. OV-9 promotes T6. OV-10 challenges the architecture but the Windows portability rationale holds.

### Task-to-Stage Mapping (addressing OV-7)

| Stage | Tasks | Dependencies |
|---|---|---|
| **Pre-Stage 1** | T5 (Node fix), T6 (REQUIREMENTS.md annotation) | None -- do before any code |
| **Stage 1** (Git + Rust + Fixtures) | T7 (cross-volume design), T21 (two-folder model spec), T22 (pixel hash format doc) | T6 done first |
| **Stage 2** (Scanner + Cache) | T1 (OOM), T2 (SQLITE_FULL), T3 (migration), T11 (I/O concurrency), E9 (WAL mode) | Stage 1 complete |
| **Stage 3** (Desktop + UI) | T14 (search), T15 (tab bar), T16 (drop zone), T18 (keyboard), T19 (zoom), T20 (responsive), T10 (Quick Look spike) | Stage 2 complete; T21 (two-folder model) informs UI |
| **Stage 4** (Quarantine) | T4 (rapid-click), T17 (banner) | Stage 3 complete |
| **Stage 6** (Release) | T8 (cargo audit), T9 (Tauri capabilities), T12 (log rotation), T13 (smoke test) | Stage 4 complete |

---

### NOT in scope (eng review)

- Frontend test framework selection -- deferred to Stage 3 implementation
- CI/CD pipeline for automated builds -- Stage 6 or post-MVP
- pHash grouping determinism with parallel insertion -- post-MVP (D3 deferred)
- Legacy review_decisions.json import -- already deferred in plan

### What already exists (eng review)

- CEO review Sections 1-11: comprehensive architecture, error, security, data flow, quality, test, performance, observability, deployment, trajectory, and design analysis
- Design review: 7 UX decisions (DD2-DD8), information architecture, keyboard map, responsive spec, accessibility baseline
- Python reference: identity(), hash_regular_file(), validate_duplicate_scope() -- safety-critical patterns for direct port
- 64 passing tests in Python -- golden fixture source for parity
- CEO Outside Voice: 8 findings integrated, 0 decisions reopened

### Worktree Parallelization Strategy

Sequential implementation, no parallelization opportunity. Single developer, staged delivery. Each stage depends on the previous. Within a stage, tasks can be done in any order.

### Failure Modes (eng review additions)

| Capability | Failure mode | Rescued? | Test? | User sees? | Gap? |
|---|---|---|---|---|---|
| Two-folder selection | User drops both folders as duplicates (no keeper root) | Need spec (OV-1) | N | Incorrect quarantine targets | **YES -- T21** |
| Group overlap | Same files in exact + pixel views | Need spec (E6) | N | Confusion, double-quarantine | **YES -- spec needed** |
| Concurrent decode | 10 parallel 24MP decodes = ~960MB | Need bound (E8) | N | Memory pressure, slowdown | **YES -- semaphore** |
| SQLite concurrent access | Reader during scan write without WAL | Need WAL (E9) | N | Stale UI data | **YES -- PRAGMA** |

### Eng Review Implementation Tasks

Synthesized from eng review findings. Each task derives from a specific finding above.

- [ ] **T21 (P1, human: ~2h / CC: ~10min)** -- docs/core -- Specify two-folder asymmetric comparison model in port
  - Surfaced by: Outside Voice OV-1 -- two-folder model with keeper protection is the core interaction pattern
  - Files: docs/designs/native-desktop-ceo-review.md, REQUIREMENTS.md s7
  - Verify: Plan specifies original-root vs duplicate-root selection, validate_duplicate_scope() port, and UI for two-role folder model

- [ ] **T22 (P2, human: ~30min / CC: ~5min)** -- docs -- Document pixel hash byte format for golden fixture parity
  - Surfaced by: E5 / OV-3 -- width+height big-endian 8-byte prefix + raw RGBA bytes is the contract
  - Files: Golden fixture spec (new), reference to app.py:48-55
  - Verify: Golden fixture exporter documents exact byte layout

- [ ] **T23 (P2, human: ~1h / CC: ~5min)** -- core -- Specify group deduplication across match categories
  - Surfaced by: E6 / OV-6 -- exact duplicates also appear as pixel-identical; UI must deduplicate or explain
  - Files: core grouping logic, frontend group display
  - Verify: Plan specifies whether exact-match groups are excluded from pixel-identical results

_T6 promoted from P2 to P1 per OV-9. T7 description corrected per OV-2: port + extend shutil.move semantics with hash verification, not design from scratch._

_No new tasks from Section 1 (Architecture) beyond IPC inventory (implementation guidance). No new tasks from Section 4 (Performance) beyond E8/E9 (implementation requirements carried as inline specs)._

### Eng Review Completion Summary

```
  +====================================================================+
  |           ENG PLAN REVIEW -- COMPLETION SUMMARY                     |
  +====================================================================+
  | Step 0: Scope Challenge    | scope accepted as-is (D2 covers       |
  |                            | structure)                             |
  | Reality rows               | 7/7 rows (PLAN_REALITY), 1 unverified |
  | Architecture Review        | 3 findings (1 WARNING, 2 OK)          |
  | Code Quality Review        | 2 findings (1 WARNING, 1 OK)          |
  | Test Review                | diagram produced, 54 gaps (greenfield) |
  | Performance Review         | 2 findings (2 WARNINGs)               |
  | NOT in scope               | written (4 items)                     |
  | What already exists        | written (5 items)                     |
  | TODOS.md updates           | 0 new proposals (no TODOS.md exists)  |
  | Failure modes              | 4 new gaps flagged                    |
  | Unresolved decisions       | 0 in this review                     |
  | Outside voice              | Claude subagent / unavailable (Codex  |
  |                            | model routing not configured). 10     |
  |                            | findings, 0 decisions reopened.       |
  | Parallelization            | sequential, no parallel lanes         |
  | Lake Score                 | N/A (no coverage-scored questions)    |
  +====================================================================+
```

### Unresolved Decisions (eng review)

None. All findings are implementation guidance with defined tasks. CEO D1-D8 and Design DD2-DD8 remain approved.

Approval readiness: PASS (all IDs approved: D1-D8 via CEO, DD2-DD8 via design; eng findings produce tasks, not decisions)

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | ISSUES OPEN | 6 proposals, 6 accepted, 1 deferred; 3 critical gaps |
| Outside Review (CEO) | Claude subagent (Codex unavailable) | Independent 2nd opinion | 1 | unavailable | 8 findings from native fallback; 0 decisions reopened |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES OPEN | 9 issues, 3 critical gaps |
| Outside Review (Eng) | Claude subagent (Codex unavailable) | Independent 2nd opinion | 1 | unavailable | 10 findings; 0 decisions reopened |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | ISSUES OPEN | score: 5/10 -> 7/10, 7 decisions |

**OUTSIDE COVERAGE:** provider=codex, phase=plan-review, outside_status=unavailable (Azure model routing not configured). Native fallback completed with 10 findings for eng review, 8 for CEO review (no outside coverage). Fix: `gstack-config set model_frontier_openai <model-id>` or `gstack-config set plan_review_tier host`.

**VERDICT:** CEO + ENG + Design reviews complete. 23 implementation tasks (T1-T23). 3 critical gaps (OOM, SQLITE_FULL, migration). Design at 7/10 pending DESIGN.md tokens. Plan is ready to implement with the task-to-stage mapping above.

NO UNRESOLVED DECISIONS
