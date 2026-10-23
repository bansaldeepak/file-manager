---
paths:
  - "documentation/**"
---

## Brief CLI — Mandatory for Documentation Mutations

Never use direct `Write`/`writeFileSync` to create or modify files under `documentation/stories/`, `documentation/todo/`, `documentation/decisions/`, or `documentation/memory/`. Always use the brief CLI — it preserves canonical record metadata (and synchronizes the tracker in legacy mode).

### Commands You Need

```bash
# Create
brief story create "Title" --feature=<folder>
brief story task create S-NNN "Task title" --priority=P0
brief todo create "Title"
brief decision create "Title"
brief memory create "Title" --memtype=feedback

# Update
brief story update S-NNN status=completed
brief story task update S-NNN-TN status=done
brief todo update TODO-NNN status=done
brief decision update DEC-NNN status=superseded
brief memory update <ID|slug|title> --body="new content"

# Retire (memory only — keeps file for audit trail)
brief memory retire <ID|slug|title>

# Read
brief story show S-NNN
brief story task S-NNN-TN
brief search "<query>"
```

### Status vocabulary — stories and tasks differ

A finished **story** is `completed`; a finished **task** is `done`. They are not interchangeable, and
use the project vocabulary consistently — an unsupported status can hide work from filtered views. Previously a typo landed silently and the story disappears from `brief completed`.

| Level | In flight | Finished | Other |
|---|---|---|---|
| Story | `planned` → `active` / `in_progress` | `completed` | `draft`, `superseded` |
| Task | `pending` | `done` | `blocked` |
| TODO | `open` | `done` | `obsolete`, `moot` |

`brief story update` rewrites the `**Status**:` header in `story.md` too, so the tracker and the story
file stay in step — but it leaves any parenthetical after the status untouched. Check that the
parenthetical is still true after the update.

### Memory commands accept ID, slug, or title

Memory files are slug-named (`deploy-process.md`), not ID-named (`MEM-001.md`). All memory
commands (`show`, `update`, `retire`) accept any of: `MEM-001`, `deploy-process`, or
`"Deploy process"`. Never delete memory — use `brief memory retire` to set `status: retired`
and stamp `valid_until`, preserving the file for audit trail.

### Records, IDs, logs and verification

In record mode (`.brief/records.json`), canonical Markdown is authoritative. New story IDs are
`feature/S-NNN` and task IDs `feature/S-NNN-T1`; use IDs returned by the CLI. Bare IDs must be
unambiguous. Preserve all existing IDs. Task progress derives from task files, not shared pointers.
`brief tracker generate --markdown` creates ignored local views; never routinely commit them.
Existing projects require a reviewed `brief tracker migrate-authority --dry-run` before explicit
migration. Do not hand-create or alter reserved `_brief` identity/metadata.

Never append to, rewrite or delete monolithic log.md/logs.md or existing standalone log entries.
Use `brief log add "outcome" --session=<id> --agent=<name> --story=<qualified-id>` for every new entry;
keep the unique files tracked. Corrections are new entries. Run `brief verify-records --base=<base>`
during review/verification and resolve violations before committing or publishing.

Direct edits to existing story/summary/task bodies are allowed for content only; preserve metadata.
Use the CLI for creation and status changes. Without CLI access, restore it before record mutations.
