---
# gstack: design-md-format=spec
name: Arcitae Dedupe
description: Precision photographic proofing tool in matte steel-gray with vermillion marking accents, evidence-visible metadata, and system-native chrome that disappears behind your photos.
colors:
  primary: "#C83C2C"       # vermillion — dark: #E05040
  on-primary: "#FFFFFF"
  surface: "#FFFFFF"         # dark: #1E2022
  text: "#1A1C20"           # dark: #E2E4E8
  text-muted: "#6B707A"     # dark: #8A8D94
  accent: "#C83C2C"         # same as primary — dark: #E05040
  success: "#2D7A4F"        # dark: #3D9A60
  warning: "#B8860B"        # dark: #DAA520
  error: "#C9342D"          # dark: #FF6961
typography:
  display:
    fontFamily: "-apple-system, SF Pro Display, Helvetica Neue, sans-serif"
    fontWeight: 500
    fontSize: "clamp(1.5rem, 2vw, 1.75rem)"
    letterSpacing: "-0.02em"
  body:
    fontFamily: "-apple-system, SF Pro Text, Helvetica Neue, sans-serif"
    fontSize: 0.875rem
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, SF Pro Text, Helvetica Neue, sans-serif"
    fontSize: 0.8125rem
    letterSpacing: "0.04em"
  mono:
    fontFamily: "ui-monospace, SF Mono, Menlo, monospace"
    fontFeature: tnum
rounded:
  sm: 4px
  md: 6px
  lg: 8px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  button-primary-hover:
    backgroundColor: "#A83020"
  input:
    borderColor: "{colors.text-muted}"
    rounded: "{rounded.sm}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
  nav-link:
    textColor: "{colors.text}"
---

# Arcitae Dedupe

## Overview

**Creative North Star:** A precision photographic proofing room — familiar macOS chrome recedes, photos take the stage, and every action is backed by visible evidence.
**Product context:** Personal photo deduplication desktop app, macOS native (Tauri 2 + React + Rust). Owner of large photo library. Category peers: Gemini 2 (MacPaw), Nektony Duplicate Finder, ForkLift 4.
**Mode per surface:** Operate (primary) — task-driven duplicate review and cleanup.
**Reference sites:** macpaw.com/gemini, nektony.com/duplicate-finder-free, binarynights.com
**Key characteristics:**
- System-native chrome that disappears (familiar macOS sidebar, toolbar, traffic lights)
- Vermillion accent communicates "proofing mark" not "danger"
- Metadata always visible beneath thumbnails (filename, dimensions, size in mono)
- Originals permanently labeled as protected throughout the UI
- Recovery (undo, quarantine, restore) as a first-class completion state

## Colors

**Strategy:** Restrained — 1 accent + neutrals. Color is rare and meaningful.
**Light or dark:** Both. prefers-color-scheme. Dark values noted inline in the YAML above.

**Ground:** Steel-gray background (#F2F3F5 light / #161819 dark) — slightly cooler than pure white/near-black, avoids the over-bright wash of pure white and the harsh contrast of pure black.

**Accent:** Vermillion (#C83C2C light / #E05040 dark). Red is reclaimed from "danger" to "proofing mark" — the language of china markers on a physical contact sheet. It appears on: selected thumbnail borders, active quarantine button, match-type labels, undo action text, and focus rings. It does NOT appear on success, warning, or destructive states, which have their own semantic tokens.

**Destructive is separate from accent:** #C9342D (slightly deeper than the vermillion) to signal irreversibility. Never use the vermillion for delete actions.

**Dark mode:** Surfaces shift to muted dark steel; accent warms slightly to #E05040 for legibility. System vibrancy applies to toolbar and sidebar materials via Tauri/macOS native.

## Typography

SF Pro family per DD6 (system font). No external font loading, no licensing. Leveraged beyond defaults via weight and scale discipline.

- **Display (SF Pro Display):** Empty states, section headings, scan completion summaries. Medium weight (500), tight tracking (-0.02em). Never competes with photos.
- **Body (SF Pro Text, 14px/1.5):** Inspector descriptions, alert text, onboarding copy. Regular weight. Max-width ~480px to keep line length readable.
- **UI (SF Pro Text, 13px medium):** Toolbar, tabs, sidebar items, button labels. Medium weight only for active/selected states — regular otherwise.
- **Mono (SF Mono, 11px, tnum):** File paths (left-truncated so filename is always visible), dimensions, file sizes, hash previews, scan counters, operation journal. Tabular figures so columns align. This is the evidence layer — the place where the app shows what it found, not just that it found something.

## Layout

- Three-pane desktop: sidebar 224px / contact sheet flex / inspector 336px. At ≥ 1200px all three panes. 900–1199px: sidebar collapses to toolbar-accessible drawer. <900px: single pane with back control.
- 8px base grid. Component padding 8–12px. Thumbnail gap 12px. Outer margins 20px. Inspector padding 16px.
- Thumbnail default 160px per DD8. Zoom slider 100–300px in 32px footer.
- Contact sheet composes as a proof sheet: thumbnails with always-visible mono metadata beneath, not a gallery wall.
- Toolbar: 52px. Tabs (Photos / Videos / All) per DD3. Persistent search per DD2, max-width 280px toward the right.

## Elevation & Depth

No zero-offset glows. Depth via offset shadows only when stacking layers (dialogs, popovers).
- App window: `box-shadow: 0 8px 32px rgba(0,0,0,0.12)`
- Cards: `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`
- Sidebar and inspector use background tint, not shadows, to separate from the contact sheet.

## Shapes

- Thumbnails: 4px (sm) — slight rounding, not bubbly.
- Buttons and inputs: 6px (md).
- Cards and panels: 8px (lg).
- No uniform large radius on everything. Nested inner radius = outer radius − gap.

## Components

- **Button primary (vermillion):** Quarantine action. Hover darkens to #A83020. Never gradient.
- **Button secondary:** Border + bg transparent. Restore, skip, cancel actions.
- **Button destructive:** #C9342D. Delete permanently. Appears only in the Quarantine view, never in the main review flow.
- **Selection state:** 2px vermillion border on thumbnail + checkmark badge. Keeper gets 2px success-green border + ORIGINAL label. Rapid double-click protected: button disabled after first click until operation resolves (T4).
- **Metadata strip:** Mono 11px beneath every thumbnail. Filename left-truncated (filename always readable at right). Dimensions and size. Never hover-only — evidence-visible is a trust design principle.
- **Inspector:** Two images at matched scale side-by-side, file details table, match-type badge (EXACT / PIXEL-IDENTICAL), quarantine button in footer. Slides in 200ms ease-out on first open per session.
- **Banner per DD5:** Post-quarantine summary with byte count and Undo. 300ms ease-out from top. Auto-dismiss 5s. Undo always available in Quarantine view after.
- **Empty state:** Display-size heading + muted body + optional action. Drop-zone variant for first-run per DD4.

## Do's and Don'ts

- Do: use vermillion only for the quarantine action, selection borders, and proofing marks.
- Do: show filename + dimensions + size beneath every thumbnail, always on.
- Do: label originals as protected everywhere they appear (lock icon + ORIGINAL badge in green).
- Do: use SF Mono for all numeric/technical data — paths, sizes, hashes, counters.
- Don't: use the accent for destructive (permanent delete) actions — use the separate error token.
- Don't: hide metadata behind hover or clicks; evidence-visible is a trust design principle.
- Don't: use gradient buttons, nested cards, colored left-border on cards, or decorative blobs.
- Don't: use system-ui without qualifying it as SF Pro Display/Text (the "I gave up on typography" default).

## Motion

- **Approach:** minimal-functional — only transitions that aid comprehension.
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms) long(400-700ms)
- **The one authored moment:** Post-quarantine banner (DD5) — 300ms ease-out from top, auto-dismiss 5s. All other transitions use system defaults or are instant.

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-10-23 | Initial design system created | Created by /gstack-design-consultation. Direction: Industrial/Utilitarian, system fonts per DD6, vermillion accent from Claude subagent PROOF direction (china-marker proofing metaphor), metadata-visible density from same. Codex Quiet Archive direction confirmed system-font discipline. Both outside voices ran and completed. |
