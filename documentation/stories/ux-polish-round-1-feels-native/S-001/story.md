---
{
  _brief:
    {
      version: 1,
      record_id: 08ee3405-36e3-4948-8a24-3cd26ff2327e,
      item:
        {
          id: ux-polish-round-1-feels-native/S-001,
          type: story,
          title: UX Polish Round 1 — Feels Native,
          status: planned,
          branch: feature/ux-polish-round-1-feels-native,
          story: documentation/stories/ux-polish-round-1-feels-native/S-001/story.md,
          link: null,
          pr: null
        }
    }
}
---
# ux-polish-round-1-feels-native/S-001: UX Polish Round 1 — Feels Native

**Status**: planned
**Branch**: feature/ux-polish-round-1-feels-native
**Created**: 2026-10-30

## Context

The native desktop app (Tauri 2 + React + Rust) shipped its MVP with scan, quarantine, restore, delete, thumbnail cache, and savings banner. The UX needs polish to feel like a real macOS app before open-source release.

This story covers the first batch of polish: the foundational stuff that makes the app feel native and correct. Round 2 (trust and design polish) follows separately.

## Scope

All changes are frontend CSS/TSX. No Rust backend changes. All work references DESIGN.md as the design system spec.

## Acceptance Criteria

- Window is draggable by the toolbar area
- All colors use design tokens (no hardcoded hex in component CSS)
- Technical data (paths, sizes, dimensions, counters) renders in mono font
- Filenames are left-truncated so the actual name is always readable
- Thumbnail placeholders show a shimmer animation while loading
- Dark mode renders correctly with no hardcoded light-only colors
- App builds and runs without errors
