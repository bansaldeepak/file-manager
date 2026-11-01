---
{
  _brief:
    {
      version: 1,
      record_id: 2b3d1b6c-5aa4-4e66-92f5-584b2da38f82,
      item:
        {
          id: ux-polish-round-2-feels-designed/S-001,
          type: story,
          title: UX Polish Round 2 — Feels Designed,
          status: planned,
          branch: feature/ux-polish-round-2-feels-designed,
          story: documentation/stories/ux-polish-round-2-feels-designed/S-001/story.md,
          link: null,
          pr: null
        }
    }
}
---
# ux-polish-round-2-feels-designed/S-001: UX Polish Round 2 — Feels Designed

**Status**: planned
**Branch**: feature/ux-polish-round-2-feels-designed
**Created**: 2026-10-30

## Context

Follows Round 1 (feels native). This round adds trust signals and design polish that make the app feel intentionally designed, not just functional.

## Scope

Frontend TSX/CSS changes. References DESIGN.md as the design system spec.

## Acceptance Criteria

- Keeper thumbnails show an ORIGINAL badge (green, lock icon) in the contact sheet
- Empty state when scan finds zero duplicates shows display-size heading + muted body
- Post-quarantine success banner appears with byte count and undo hint (DESIGN.md DD5)
- Scan progress shows phase labels (walking, hashing, grouping) and file counts
- App builds and runs without errors
