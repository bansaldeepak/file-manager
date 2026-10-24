---
name: native-desktop-planning
description: Owner requested Rust desktop migration planning with fast loading, improved UX, and early testing.
metadata:
  type: project
created: 2026-10-22
updated: 2026-10-22
valid_until: 2027-01-22
importance: 4
---

# Native desktop planning

- **Source:** Owner's 2026-10-22 request to plan a Rust-based system for proper testing, a nice UI/UX, and much faster loading, after accepting the improved two-folder comparison.
- **Scope:** Native desktop migration in this repository. Planning is authorized; this statement does not approve an implementation execution mode or publication.
- **Decided:** Carry the accepted original-plus-optional-duplicate workflow into planning. Existing `REQUIREMENTS.md` specifies Tauri 2, React, TypeScript, Rust, Apple Silicon first, incremental Python parity, and safe local operations.
- **Proposed:** Golden baseline → fast exact discovery → read-only desktop preview → safe cleanup alpha → pixel/perceptual parity → release testing. This ordering and numeric performance targets await owner review.
- **Apply:** Preserve the working Python application and personal data, isolate native app storage, and measure candidate filtering, cold/warm scans, visible previews, and UI latency independently.
- **Evidence:** Rust, Node, pnpm, and Apple Command Line Tools are installed. No Tauri build, Rust dependencies, native benchmarks, or packaged launch has been verified.
- **Proposal:** [Native desktop PRD](../documentation/stories/native-desktop/PRD.md). No implementation tasks, workflow initialization, or migration was run during planning.
