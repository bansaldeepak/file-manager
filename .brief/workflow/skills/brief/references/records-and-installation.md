# Portable installations and concurrent records

Read this contract when setting up a project, planning/creating records, executing tasks, or reviewing
Brief-managed changes. The selected execution mode never relaxes these storage rules.

## Installation

- `brief install` installs the machine workflow package from installed CLI assets. Preview with
  `--dry-run`; repeated installs stay pinned. Brief is CLI-only; there is no MCP setup or server.
- Recommend `brief init --scope=local` for teams: `.brief/workflow/` contains real, pinned skills,
  rules and agents; commit the bundle, relative registrations and managed instruction changes.
- `--scope=global` selects the independent home package at `~/.brief/workflow/`. Each machine must
  install it. Project-local bundles take precedence over global skills. The CLI runtime is separate.
- Repeated init preserves the selected scope/version. Updates are explicit:
  `brief update --check`, `brief update --dry-run`, then authorized `brief update --apply`.
  Add `--global` for the machine package. No source argument is needed for npm or npm-linked use:
  project init/update defaults to the home package, then CLI assets; global operations use CLI assets.
  `--source=<path>` explicitly selects a local checkout/package or directory symlink. URLs are not
  fetched. A global update only offers an update to pinned local copies.
- Preserve custom files and outside-block instructions. Never delete a real directory to replace it
  with a link. Resolve ownership/customization conflicts before writing. `brief doctor` detects
  missing registrations and incomplete transactions; `brief update --recover` restores only owned
  transaction changes and refuses to overwrite later edits. Notices support `--notice=on|off|snooze`.

## Authoritative records

- `.brief/records.json` selects canonical Markdown authority. Every story/item contains a reserved
  `_brief` envelope with immutable identity and complete metadata. Preserve it during content edits.
- `brief story/item/memory` mutations update individual files. Do not edit tracker views or shared
  current_task/last_task pointers. Task progress derives from individual task files.
- `documentation/tracker.yaml` and `documentation/PROJECT-TRACKER.md` are ignored LOCAL views in
  record mode. Generate only when needed with `brief tracker generate --markdown`; never routinely
  commit them. CLI reads canonical records even when the views are stale or absent.
- Existing projects stay in legacy mode until an explicit migration. First run
  `brief tracker migrate-authority --dry-run`; inspect mappings and preserve all unknown metadata.
  Apply only within user-authorized scope, then untrack views using the printed command. Conflicting,
  missing or malformed records stop migration. Historical logs remain untouched.
  Resolve reported field differences against recorded decisions; do not regenerate the legacy
  tracker to silence conflicts. Record status comes from frontmatter or record-header metadata;
  narrative memory status and section-local experiment statuses remain prose.
- `brief tracker rollback-authority --apply` restores exact migration inputs only when no later edits
  or new records would be lost. Incomplete migrations block normal work until recovery.

## IDs and concurrent work

- New record-mode story IDs are `feature-name/S-001`; task IDs are `feature-name/S-001-T1`.
  Use the ID returned by `brief story create --feature=<slug>`, not a manually guessed counter.
  The physical path remains `documentation/stories/<feature>/S-001/`.
- Different features can reuse S-001. Existing global IDs remain valid. Bare IDs work only when
  unambiguous; resolve reported alternatives explicitly. Same-feature independent allocations can
  conflict and require reconciliation. Never resolve identities with first-wins/ours/theirs/union.
- Without the CLI, read canonical Markdown. Do not fabricate `_brief` metadata or use a generated
  tracker as authority; restore CLI access before record-mode creation/status changes.

## Immutable logs and verification

- Never create, append to, rewrite or delete historical `log.md`/`logs.md`. Keep their bytes intact.
- Always use `brief log add "outcome" --session=<session> --agent=<agent> --story=<qualified-id>`.
  Every entry is a separate unique file under `documentation/logs/`; record session and agent where
  known. Never rewrite an existing entry or maintain a shared mutable session manifest. Corrections
  are new entries linked to the earlier entry. Keep these collaboration records tracked.
- Run `brief verify-records --base=<review-base>` before local review/commit/publication and after
  merges that combine agent work. A nonzero result blocks readiness until corrected. It detects
  invalid/duplicate record identities, merge markers, immutable-log changes and tracked view edits.
  Preserve custom CI/hooks; integrate this check with existing required checks rather than replacing them.
- Independent files reduce conflicts between different records. Concurrent edits to the same story,
  task, preference or code still need ownership coordination and normal conflict resolution.
