# Local Media Cleaner
## Product Requirements and Implementation Specification

**Document status:** Implementation-ready specification  
**Primary audience:** Codex coding agent and maintainers  
**Initial platform:** macOS on Apple Silicon  
**Future platform:** Windows  
**Distribution goal:** Open source, local-first desktop application anyone can build and install  
**Architecture:** Tauri 2, React, TypeScript, Rust  
**Migration approach:** Incremental migration from the existing Python photo-deduplication application with automated parity tests

---

## 1. Mission

Build a reliable, approachable desktop application that helps people find and safely clean duplicate or visually similar media files on their own computers.

The application must run locally. Users must not need an account, cloud service, or network connection for scanning, comparison, review, quarantine, or restoration.

The first release targets macOS on Apple Silicon. The architecture must keep the core engine and most UI behavior portable so Windows support can be added later.

The existing Python application is the behavior reference for photo duplicate detection until the Rust implementation passes the defined parity tests. Do not remove or silently change established behavior during migration.

## 2. Product principles

1. **Local-first and privacy-preserving.** Do not upload file names, paths, images, videos, hashes, or scan results.
2. **Safe by default.** Never permanently delete files automatically. Use a review and quarantine workflow.
3. **Explainable results.** Show why files are grouped together and distinguish exact duplicates from visual similarity.
4. **No destructive surprises.** Confirm operations, handle errors visibly, and preserve recovery information.
5. **Incremental scanning.** Cache metadata and hashes so unchanged files do not need expensive reprocessing.
6. **Portable core.** Keep media analysis and file-operation logic independent of Tauri and React.
7. **Open-source first.** Include license, contribution instructions, reproducible development setup, tests, and public release build instructions.
8. **Accessibility and usability.** Support keyboard navigation, clear labels, readable progress and error states, and practical preview controls.

## 3. Scope

### 3.1 First public MVP

- Native desktop shell using Tauri 2.
- React and TypeScript interface.
- Rust media-scanning and duplicate-detection engine.
- macOS Apple Silicon development and release build.
- User-selected folder scanning.
- Exact file duplicate detection.
- Pixel-identical image detection after documented normalization.
- Perceptual image similarity detection.
- Duplicate groups with preview, metadata, and keeper suggestions.
- User-controlled selection of files to quarantine.
- Quarantine review, restore, and explicit permanent deletion.
- Local SQLite cache and review/action history.
- Cancellation, progress reporting, and recoverable error handling.
- Unit tests, integration tests, Python-to-Rust parity tests, and packaging smoke tests.
- Open-source repository and build documentation.

### 3.2 Next phase: video

Design the media-analyzer interface in the MVP so video support can be added without redesigning the application. Implement video analysis after photo parity and the safe file workflow are stable.

Initial video capabilities:
- Exact byte-level duplicate detection.
- Metadata extraction such as duration, dimensions, codec, and file size.
- Thumbnail or sampled-frame generation.
- Frame-fingerprint-based similarity as a later increment.
- Human review for similar, edited, resized, or trimmed videos. Do not automatically classify a partial visual match as a safe duplicate.

### 3.3 Later scope

- Audio duplicate detection.
- Documents and other file types.
- Large-file discovery.
- Optional similarity features with clearly explained thresholds.
- Windows x64 build and installer.
- Signed/notarized public macOS releases and automated release artifacts.

### 3.4 Out of scope for the first MVP

- Cloud scanning or account-based services.
- Automatic permanent deletion.
- AI-based semantic photo understanding.
- Background monitoring of the entire computer without explicit opt-in.
- Windows release before the macOS core is stable.
- Requiring users to install Python, Node.js, Rust, or FFmpeg merely to run a published release. Development tools may be required to build from source.

## 4. Target architecture

Use a monorepo. Keep the core engine as a Rust workspace library, independent of Tauri commands and the frontend.

```text
local-media-cleaner/
├── apps/
│   └── desktop/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── scan/
│       │   │   ├── photos/
│       │   │   ├── videos/
│       │   │   ├── review/
│       │   │   └── quarantine/
│       │   ├── hooks/
│       │   ├── lib/
│       │   └── types/
│       ├── src-tauri/
│       │   ├── src/
│       │   │   ├── commands/
│       │   │   ├── events/
│       │   │   └── lib.rs
│       │   ├── capabilities/
│       │   ├── icons/
│       │   └── tauri.conf.json
│       └── package.json
├── crates/
│   ├── media-core/
│   ├── scanner/
│   ├── image-analyzer/
│   ├── duplicate-engine/
│   ├── media-index/
│   └── safe-files/
├── tests/
│   ├── fixtures/
│   ├── golden/
│   └── parity/
├── legacy/
│   └── python-dedupe/
├── scripts/
├── docs/
├── Cargo.toml
├── pnpm-workspace.yaml
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

This is the intended destination structure, not a requirement to create empty crates. Codex should establish the minimum useful workspace first and introduce crates when they provide real separation.

### 4.1 Responsibilities

- `media-core`: shared domain types, media identifiers, analyzer traits, errors, and result models.
- `scanner`: directory traversal, exclusions, symlink policy, file eligibility, cancellation, and progress.
- `image-analyzer`: image decoding, EXIF orientation handling, normalized pixel fingerprints, perceptual hashes, dimensions, and format metadata.
- `duplicate-engine`: exact duplicate grouping, similarity matching, thresholds, deterministic keeper recommendations, and explanation of match type.
- `media-index`: SQLite schema, migrations, file metadata cache, scan records, and review history.
- `safe-files`: quarantine, restore, permanent deletion, collision handling, validation, and operation journal.
- `apps/desktop/src-tauri`: narrow Tauri commands and event forwarding only. Do not put core algorithms here.
- `apps/desktop/src`: user interface and view state. Do not implement hashing or filesystem mutations in the frontend.

### 4.2 Candidate libraries

Use current stable versions compatible with the selected toolchain, pin dependencies in lockfiles, and verify license and platform support before adoption.

- Desktop: Tauri 2 and `tauri-plugin-dialog`.
- Frontend: React, TypeScript, Vite, and pnpm.
- Rust serialization: `serde`, `serde_json`.
- Directory traversal: `walkdir` or `ignore`.
- Parallel processing: `rayon`.
- File hashing: `sha2` or `blake3`.
- Image decoding: `image`.
- EXIF metadata: `kamadak-exif`, with explicit orientation normalization.
- Perceptual hashing: evaluate `imghash` or another compatible implementation against Python ImageHash. Do not assume equivalence without tests.
- SQLite: `rusqlite`, with a deliberate bundled-versus-system SQLite decision.
- Error handling: `thiserror`.
- Logging: `tracing` and a local log strategy that does not expose sensitive paths by default.
- Video phase: FFmpeg as a subprocess initially, with a clear distribution and licensing plan before shipping it.

Avoid adding dependencies without a concrete need. Review each dependency's license, maintenance status, security posture, and macOS/Windows support.

## 5. File scanning and identification

### 5.1 User-selected roots

- Let the user select one or more folders through a native folder picker.
- Show the selected roots before starting the scan.
- Provide exclusions and a clear policy for hidden files, package contents, symlinks, aliases, and application-managed folders.
- Do not follow symlinks by default unless explicitly supported and documented.
- Avoid scanning the app's own database, logs, quarantine folder, and temporary thumbnails as source media.
- Never silently expand the scan to the user's whole home directory or disk.

### 5.2 Scan progress and cancellation

- Long-running work must not block the UI thread.
- Report scan ID, phase, completed count when known, total count when known, and current phase.
- Support cancellation and clean up temporary work.
- Cancellation must not leave half-completed destructive operations.
- Clearly distinguish completed, cancelled, partially completed, and failed scans.

### 5.3 Cache invalidation

Store normalized path, file size, modification timestamp, and relevant analyzer version alongside computed fingerprints. Metadata may be used as a cache hint but must not be treated as cryptographic proof that content is unchanged.

- Recompute required fingerprints if file size, modification time, analyzer version, or other validation signals change.
- Handle missing, moved, renamed, unreadable, and replaced files.
- Provide a way to clear and rebuild the local index.
- Keep database schema migrations versioned.
- Do not persist stale duplicate groups as current without revalidating their member files.

## 6. Duplicate detection requirements

The UI and engine must keep these categories distinct.

### 6.1 Exact file duplicates

- Compute a cryptographic content hash such as SHA-256 or BLAKE3.
- Files are exact byte duplicates only when their content hashes match, with size checks used as an efficient preliminary filter.
- Hash equality should be the basis for grouping, with appropriate defensive handling of read errors.
- Filenames and paths do not determine duplicate identity.

### 6.2 Pixel-identical images

Normalize images using a documented, deterministic pipeline before comparison. The initial compatibility target is the current Python app's behavior, including EXIF orientation correction and conversion to RGBA pixels.

Test:
- EXIF orientation.
- RGB, RGBA, grayscale, and palette formats.
- Alpha channels and transparency.
- Image dimensions.
- Corrupt and unsupported files.
- Different encodings that decode to identical normalized pixels.

Do not claim images are pixel-identical if dimensions or normalized pixel content differ.

### 6.3 Perceptually similar images

- Implement perceptual hashing with documented preprocessing and hash size.
- Use Hamming distance for hash comparison.
- Initially preserve the existing Python application's threshold behavior, including its default threshold of 6 if confirmed by the reference implementation.
- Explain that a threshold is a similarity heuristic, not proof of duplication.
- Lower thresholds should be stricter; higher thresholds should be more permissive.
- Similarity results must remain reviewable. Never automatically quarantine or delete a file just because its perceptual hash is close.
- Use an efficient index such as a BK-tree or another justified strategy when scale requires it.
- Ensure deterministic grouping and avoid duplicate group membership inconsistencies.

### 6.4 Keeper suggestion

Initially preserve the Python reference ordering:
1. Prefer greater pixel area/resolution.
2. Then prefer larger file size.
3. Then use a deterministic path ordering as a tie-breaker.

Present the keeper as a suggestion, not an irreversible decision. Let the user choose another keeper.

### 6.5 Result explanation

Each duplicate group must display:
- Match category: exact bytes, pixel-identical, or perceptually similar.
- Match distance/threshold when applicable.
- File path or clearly accessible location.
- File size, dimensions, and relevant media metadata.
- Preview where supported.
- Suggested keeper and reason.
- Any analysis errors or missing metadata.

## 7. User experience requirements

### 7.1 Primary navigation

Provide clear sections:
- Scan
- Photo duplicates
- Video duplicates, when implemented
- Review queue
- Quarantine
- Settings/about

Do not hide important actions in an ambiguous UI. Every destructive or recovery workflow must be discoverable.

### 7.2 Scan screen

- Choose folders.
- Configure supported scan types and similarity threshold.
- Start, cancel, and view progress.
- Show scan summary and any skipped or unreadable files.
- Explain whether results come from a new scan or a cached index.

### 7.3 Duplicate review

- Group related files together.
- Show useful previews and metadata side by side or in a grid.
- Provide a suggested keeper.
- Allow users to select exactly which files to quarantine.
- Provide group-level and file-level actions, with clear selection counts.
- Before a bulk operation, show the number of files and estimated bytes affected.
- Do not include the suggested keeper in the selected-to-quarantine set by default.
- Prevent an operation that would remove every available copy in a group unless the user explicitly overrides a clearly worded safety guard.

### 7.4 Quarantine review

- Provide a dedicated, visible Quarantine section.
- List quarantined items with original paths, quarantine paths, timestamps, and operation status.
- Allow preview of supported media.
- Allow restore to the original path.
- If the original path is occupied, never overwrite. Offer a deterministic conflict resolution, such as a unique suffix.
- Permanent deletion must require an explicit user action and confirmation.
- Clearly state that permanent deletion may be irreversible.
- Never provide a one-click bulk permanent deletion without a separate, explicit confirmation step.

### 7.5 Restore and action history

- Record operations in a durable local journal.
- Record source path, destination path, timestamp, action, and status.
- Support safe recovery after an interrupted move where possible.
- Make errors actionable without silently swallowing them.
- Do not include raw personal paths in telemetry. The first release should have no telemetry.

## 8. Safe filesystem operations

This is a high-risk area and must receive dedicated tests.

### 8.1 Quarantine

- Use a documented quarantine location. Prefer an app-managed directory on the same volume as the source where practical, or another safe location with clearly communicated move semantics.
- Preserve enough relative-path information to restore files.
- Use atomic rename/move when possible on the same filesystem.
- If a cross-volume move is required, use a verified copy-then-rename workflow, verify the destination content, and only then remove the source.
- Never overwrite an existing file.
- Revalidate source existence, file identity signals, and expected metadata immediately before the operation.
- If a move fails, preserve the source and report the failure.
- Do not silently discard files when the database or journal cannot be updated.

### 8.2 Permanent deletion

- Only permit deletion of items already in quarantine.
- Require explicit selection and confirmation.
- Revalidate the target and ensure it is inside the configured quarantine root.
- Never trust a path supplied by the frontend without backend validation.
- Protect against path traversal and symlink attacks.
- Record a result for each item in bulk operations.
- Explain that secure overwrite is not guaranteed on modern filesystems, SSDs, snapshots, or copy-on-write filesystems.

### 8.3 Restore

- Verify the item is still inside quarantine.
- Reconstruct the original path from trusted journal metadata.
- Never overwrite an existing destination.
- Verify successful restoration and update the journal and index.
- Support restoring an individual item even if another item in its group is missing.

### 8.4 Database and filesystem consistency

Filesystem moves and SQLite transactions cannot generally be committed as one atomic transaction. Implement an operation journal/state machine so interrupted operations can be detected and reconciled on startup. Test crash-like interruptions between each operation step.

## 9. Python-to-Rust parity strategy

The existing Python implementation is the behavior reference until migration is accepted. Do not delete it before the parity suite is passing.

### 9.1 Golden fixtures

Create a small redistributable fixture dataset containing:
- Byte-identical copies with different names.
- Same decoded pixels saved in different formats.
- Resized images.
- Recompressed images.
- EXIF-rotated images.
- Transparent and grayscale images.
- Visually similar but distinct images.
- Corrupt or unsupported files.
- Three-or-more-member groups.
- Keeper-selection ties.
- File paths with Unicode, spaces, and unusual but valid characters.

Do not include copyrighted or personal user media in the public test fixtures. Generate synthetic fixtures or use assets with clear redistribution rights.

### 9.2 Parity outputs

The Python reference runner should produce stable JSON results containing:
- Fixture identifiers.
- Normalized dimensions and metadata.
- Pixel fingerprints where relevant.
- Perceptual hashes and pairwise distances.
- Duplicate groups and category.
- Suggested keeper.
- Errors for invalid fixtures.

The Rust implementation should produce the same schema or a well-documented normalized schema for comparison.

### 9.3 Acceptance criteria

- Exact file duplicate groups match the reference.
- Pixel-identical groups match the reference for the documented normalization contract.
- pHash outputs and distances match the reference when claiming compatibility. If exact compatibility is impossible, document the discrepancy and make a deliberate versioned decision.
- Keeper suggestions match the reference for parity fixtures.
- Similarity threshold boundaries are tested, including distances at threshold minus one, exactly at threshold, and threshold plus one.
- Errors and unsupported inputs are handled without crashing the whole scan.
- Test runs do not mutate the source fixture files.

### 9.4 Performance tests

Benchmark with reproducible synthetic datasets and record:
- Total files scanned.
- Time for initial scan.
- Time for unchanged rescan.
- Hashing throughput.
- Peak memory.
- UI responsiveness during scan.
- Duplicate grouping time.

Do not promise a specific speedup until measurements on target hardware are available.

## 10. Video analyzer design

Implement video after the photo MVP is stable.

### Phase A: exact duplicates and metadata
- Reuse the exact file hashing engine.
- Extract duration, resolution, codec, frame rate where available, and file size.
- Generate thumbnails using a managed FFmpeg invocation.
- Handle missing or malformed metadata gracefully.

### Phase B: visual similarity
- Sample frames with a documented, deterministic strategy.
- Compute frame fingerprints and compare sequences.
- Distinguish identical files, visually similar full clips, and likely partial/trimmed matches.
- Show confidence and evidence in the UI.
- Do not imply audio equivalence based only on frame similarity.
- Never automatically delete or quarantine based on video similarity.

### Distribution and licensing
- Decide whether FFmpeg is bundled, downloaded separately, or supplied by the user.
- Prefer a reproducible and secure distribution strategy for published releases.
- Document FFmpeg and codec licensing obligations for the exact binaries and configuration shipped.
- Verify the licensing of every bundled dependency before release.

## 11. Privacy and security

- No network calls required for scanning or cleaning.
- No accounts or telemetry in the MVP.
- Store index and operation journal in the user's app-data directory.
- Do not log image content or unnecessarily expose personal file paths.
- Restrict Tauri capabilities to the minimum required.
- Keep file operations in Rust and validate all frontend arguments.
- Avoid broad filesystem permissions when folder-scoped access can work.
- Document all local data the application stores and how users can clear it.
- Treat media files as untrusted input. Handle malformed files, resource exhaustion, and subprocess failures safely.
- Use dependency auditing and keep dependencies updated.
- Publish a security reporting policy.

## 12. Open-source requirements

The repository must be suitable for public use and contribution from the first public release.

### 12.1 License

Use a permissive license such as **MIT** unless the maintainers choose another license before publishing. Include the complete license text and copyright attribution. Review all dependencies and assets for compatibility.

### 12.2 Required repository files

- `README.md`: overview, features, screenshots, privacy statement, installation, development, troubleshooting, supported platforms, and release status.
- `LICENSE`: chosen open-source license.
- `CONTRIBUTING.md`: development setup, tests, code style, and pull-request process.
- `CODE_OF_CONDUCT.md`: community expectations.
- `SECURITY.md`: supported versions and private vulnerability reporting instructions.
- `CHANGELOG.md`: user-visible changes.
- `docs/architecture.md`: architecture and key decisions.
- `docs/building.md`: build instructions for macOS and later Windows.
- `docs/testing.md`: test suite and parity procedure.
- `docs/privacy.md`: local storage and network behavior.
- `docs/dependency-licenses.md`: inventory and obligations for bundled dependencies.

### 12.3 Build from source

A contributor should be able to:
1. Install documented development prerequisites.
2. Clone the repository.
3. Install frontend dependencies using the lockfile.
4. Run Rust tests and frontend tests.
5. Launch the desktop app in development mode.
6. Build a local installer.
7. Run parity tests against the Python reference fixtures.

Document prerequisites accurately. Published installers should not require contributors' development tools.

### 12.4 Public release workflow

- Use CI for formatting, linting, unit tests, integration tests, parity tests, and frontend checks.
- Build macOS Apple Silicon release artifacts.
- Add Windows x64 jobs after Windows support is implemented.
- Publish checksums for release artifacts.
- Use signed and notarized macOS releases when the maintainer has the necessary Apple Developer credentials.
- Do not put signing certificates, secrets, or private tokens in the repository.
- Provide a reproducible version/tagging process and release notes.
- Do not claim an artifact is signed or notarized unless the release pipeline verifies it.

### 12.5 Installation experience

For users:
- Provide a release download and clear installation steps.
- Explain Gatekeeper warnings only as appropriate to the actual signing status. Do not instruct users to disable macOS security globally.
- Explain how to verify downloads and report issues.
- Keep the application usable offline after installation.

## 13. Testing strategy

### Rust
- Unit tests for hashing, normalization, grouping, threshold behavior, keeper selection, path validation, and state transitions.
- Integration tests for scans, cache invalidation, quarantine, restore, and deletion.
- Property-based tests where useful for path and grouping invariants.
- Fault-injection tests for filesystem errors and interrupted operations.

### Frontend
- Component tests for selection, preview state, filtering, progress, and confirmation dialogs.
- Tests that bulk actions display correct counts and cannot silently select unintended files.
- Accessibility checks for key workflows.

### End-to-end
- Launch the desktop app against temporary test directories.
- Verify folder selection, scan completion, duplicate review, quarantine, restore, and permanent deletion.
- Verify that cancellation does not corrupt the index or source files.
- Verify first-run and permission-denied states.

### Packaging
- Build and launch the actual packaged `.app`.
- Test the DMG on a clean macOS account or machine.
- Confirm the app works without Python or development tools installed.
- Verify bundled resources and dependencies.
- Confirm app data is stored in documented locations.

## 14. Definition of done for the photo MVP

The MVP is not complete until all of the following are true:

- [ ] App launches as a macOS desktop application.
- [ ] Published build does not require Python, Node.js, or Rust to be installed.
- [ ] Users can select a folder and scan supported image formats.
- [ ] Exact, pixel-identical, and perceptually similar matches are distinguishable.
- [ ] Similarity threshold and keeper suggestion follow documented rules.
- [ ] Rust parity tests pass against the agreed Python reference fixtures.
- [ ] Progress, cancellation, unreadable files, and errors are handled.
- [ ] Unchanged rescans use the local cache correctly.
- [ ] Users can review duplicate groups and choose what to keep.
- [ ] Selected files can be quarantined safely.
- [ ] Quarantined items can be previewed and restored without overwriting files.
- [ ] Permanent deletion is available only for quarantined items and requires confirmation.
- [ ] The operation journal can reconcile interrupted operations.
- [ ] No source file is deleted or overwritten by automated tests.
- [ ] No telemetry or upload is performed.
- [ ] CI passes Rust, frontend, parity, and integration tests.
- [ ] A signed/notarized installer is produced if release credentials are available; otherwise the unsigned status is clearly documented.
- [ ] Open-source license, documentation, contribution, security, and dependency-license files are present.

## 15. Instructions to Codex

Work incrementally. Do not attempt a large untested rewrite in one pass.

1. Inspect the existing repository and identify the current Python app, its detection behavior, cache format, review workflow, and tests.
2. Create a concise implementation plan and identify any unknowns before changing behavior.
3. Preserve the Python app as the reference until parity is established.
4. Set up the Rust workspace and golden fixtures first.
5. Implement and test the core detection algorithms before building the UI.
6. Commit changes in logical, reviewable increments if Git is available.
7. Run relevant tests after each step and report actual command output and failures. Do not claim tests passed if they were not run.
8. Build and launch the app locally when the environment supports it. If packaging or UI testing cannot be performed in the current environment, state that clearly and provide exact steps for the maintainer to run on a Mac.
9. Never run destructive tests against real user directories. Use generated temporary fixtures.
10. Do not delete the existing Python implementation, user data, cache, or quarantine contents without explicit approval.
11. Do not silently change detection thresholds or the keeper algorithm.
12. Do not add video similarity until photo parity and safe file operations pass.
13. Before publishing, verify dependency and bundled-asset licenses and complete the open-source release documentation.
14. At the end of each milestone, summarize files changed, tests run, results, known gaps, and the next milestone.

### First Codex task

**Begin with repository inspection and Milestone 1 only.** Produce:
- A short inventory of the existing Python behavior and dependencies.
- The Rust workspace skeleton.
- A minimal golden fixture set using redistributable or generated assets.
- A Python reference-output generator.
- Rust unit tests for exact hashing, image normalization, pHash distance, and keeper selection.
- A parity test command documented in `docs/testing.md`.

Do not build the complete desktop UI or implement video similarity in the first task. Establish a trustworthy, reproducible parity baseline first.
