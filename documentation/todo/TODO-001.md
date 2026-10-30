---
id: TODO-001
title: Use macOS Trash for permanent delete instead of remove_file
priority: P1
status: open
created: 2026-10-24
story: null
link: null
_brief:
  version: 1
  record_id: e857bc7f-0b7c-4162-9dd5-9de2607d70c9
  item:
    id: TODO-001
    type: todo
    title: Use macOS Trash for permanent delete instead of remove_file
    status: open
    priority: P1
    link: null
    pr: null
---

## What

Use macOS Trash for permanent delete instead of remove_file

## Why

## What
When the user triggers 'permanent delete' on quarantined files, send them to
macOS system Trash via `trash` crate (or NSFileManager trashItem) instead of
std::fs::remove_file. This gives the user a final recovery window via Finder.

## Why
User request 2026-10-24: 'not to permanently delete rather add to user bin
and there user can always bring back and verify etc'. Matches macOS UX norms.
The quarantine folder already provides a first safety layer; Trash provides a
second before bytes are gone.

## Implementation notes
- `trash` crate (crates.io): cross-platform, moves to OS trash on macOS/Windows/Linux
- Alternative: `objc2-app-kit` / `NSFileManager.trashItem(at:)` for macOS-native
- The journal op 'delete' would record the original quarantine path and the trash URL
- No change to the quarantine journal schema needed (trash path returned by API, not stored)

## Affected tasks
- T-021 (quarantine journal) — delete command currently calls remove_file
- Future: delete Tauri command (not yet implemented)

## Blocked by
UI layer (T-014) for the delete command itself

## Context

<!-- Where in the code this lives. Relevant files, functions, constraints. -->

## Resolution

_Filled when done:_
- Resolved by: <!-- S-NNN / inline fix -->
- PR: <!-- #NNN -->
- Date: <!-- YYYY-MM-DD -->
