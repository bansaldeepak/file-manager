---
{
  _brief:
    {
      version: 1,
      record_id: 6c007545-d801-49d0-b629-a6870cb2c3a2,
      item:
        {
          id: native-desktop/S-001,
          type: story,
          title: Native Desktop App (Tauri 2 + React + Rust),
          status: planned,
          branch: feature/native-desktop,
          story: documentation/stories/native-desktop/S-001/story.md,
          link: null,
          pr: null
        }
    }
}
---
# native-desktop/S-001: Native Desktop App (Tauri 2 + React + Rust)

**Status**: planned
**Branch**: feature/native-desktop
**Created**: 2026-10-23

## Context
Migrate the Python/Streamlit photo deduplication tool to a native macOS desktop app. Three rounds of review (CEO D1-D8, design DD2-DD8, eng E1-E9) are complete. PRD, TRD, and DESIGN.md are approved. This story covers the full migration in 6 stages with 28 tasks.

## Goal
Deliver a native macOS desktop app that performs exact + pixel-identical photo deduplication with keyboard-driven review, quarantine/restore safety, and the design system in DESIGN.md — replacing the Streamlit prototype for daily use.

## User Story
As a photographer managing a large personal library, I want a native app that scans for duplicates, shows me visual evidence before I act, and moves files safely so that I can reclaim space without risking photo loss.

## Acceptance Criteria
- [ ] Rust workspace builds clean: cargo build --workspace
- [ ] Parity tests pass: SHA-256, pixel hash, keeper ordering match Python golden fixtures
- [ ] Scanner processes 30K images in under 3 minutes cold on SSD
- [ ] Quarantine → restore round-trip leaves original library unchanged
- [ ] Journal crash recovery: app reconciles PENDING operations on startup
- [ ] All 11 keyboard shortcuts work (DD7)
- [ ] No OOM crash on images > 32768px dimension (T-008 enforced)
- [ ] SQLITE_FULL surfaces "disk full" message, not silent failure
- [ ] No duplicate quarantine action on rapid double-click

## Scope
**In scope:** Exact dedup (SHA-256) + pixel-identical dedup (EXIF-corrected RGBA hash), Tauri 2 + React + Rust desktop app, three-pane UI per DESIGN.md, quarantine/restore with operation journal, WebP thumbnail cache, drag-and-drop folder selection, macOS Quick Look spike (D5), keyboard shortcuts (DD7), responsive layout.

**Out of scope:** pHash perceptual matching (deferred D3), video/audio dedup, Windows build, cloud scanning, signed/notarized release, legacy Python cache import.

## Risk and Verification
**P1 critical gaps (T-008, T-009, T-010):** OOM on huge images, SQLITE_FULL, migration failure dialog — must be addressed before Stage 2/3 can be considered stable.
**Cross-volume quarantine (T-006):** New requirement, not a Python port. Requires design + fault injection tests.
**Quick Look feasibility (T-013):** macOS-specific Objective-C bridging. Spike required; fallback to Finder preview if QLPreviewPanel is sandboxed out.
**Browser checkpoints:** Three-pane layout renders correctly (T-014), thumbnail metadata always visible, quarantine confirm single-fires (T-023).
**Automated coverage:** Rust parity tests (T-007), journal state machine tests (T-021), OOM skip test (T-008), SQLITE_FULL test (T-009), migration failure test (T-010).

## Execution Policy
Selection is made by the user at implementation start; never pre-approve a mode during planning.

## References
- documentation/stories/native-desktop/PRD.md
- documentation/stories/native-desktop/TRD.md
- DESIGN.md (design system — read before any UI task)
- AGENTS.md (project conventions)
- REQUIREMENTS.md (s3.1, s8, s11 — safety + security invariants)
