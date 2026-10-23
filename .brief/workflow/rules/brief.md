---
paths:
  - "documentation/**"
  - "*.md"
---

# Brief — Project Context Tool

Project management CLI. If `brief` is in PATH, use it for lookups and mutations.
Run `brief help` for full command reference.

## Quick Reference

```bash
# Search (works immediately — reads files, no setup needed)
brief search "<query>"              # all types
brief search "<query>" --todo       # filter by type

# Views (tables)
brief story list                    # active stories
brief todo list                     # open TODOs
brief decision list                 # active decisions
brief status                        # summary counts
brief pending                       # all open items
brief active                        # all in_progress
brief stats                         # usage per day (current project)
brief stats --global                # usage across all projects

# Story detail
brief story tasks S-001             # task table
brief story task S-001-T2           # single task content

# Create (--body for full content, or omit for template)
brief story create "Feature name" --body="## Context\n..."
brief story task create S-001 "Task title" --body="## Description\n..."
brief todo create "Fix the thing" --body="Because X breaks"
echo "full content" | brief story create "Title"   # stdin pipe also works

# Read
brief story show S-001              # full story.md
brief story task S-001-T2           # full task file
brief story summary S-001           # summary.md content
brief todo show TODO-001            # full todo .md
brief context show <slug>           # full context file

# Update (--body replaces full content below metadata header)
brief story update S-001 status=done pr=#42
brief story update S-001 --body="new full content"
brief story task update S-001-T2 status=done
brief story task update S-001-T2 --body="new task content"
brief story summary update S-001 --body="## What Changed\n..."
brief todo update TODO-001 status=done "note=Resolution details"
brief todo update TODO-001 --body="new body"
brief context update <slug> --body="new content"

# Bug tracking
brief bug create "Description" --severity=critical --body="## Steps\n..."
brief bug list                      # open bugs
brief bug show BUG-001              # full bug file
brief bug update BUG-001 status=done

# Memory management
brief memory create "Key insight" --memtype=feedback --body="Details"
brief memory list                   # active memories
brief memory show <slug>           # full memory file
brief memory retire <slug>

# Log (multi-agent safe — one file per entry)
brief log "What happened" --tag=progress --story=S-001
brief log "Summary" --body="detailed multi-line content"
brief log list                      # recent entries
brief log list --tag=progress       # filter by tag

# Tracker management
brief tracker generate              # rebuild tracker.yaml from filesystem
brief tracker generate --markdown   # same + regenerate PROJECT-TRACKER.md
brief tracker generate --dry-run    # preview without writing
brief tracker show                  # current canonical metadata (legacy: raw tracker)
brief verify-records --base=<base>  # required record/log integrity check

# Utilities
brief next story --feature=checkout # preview checkout/S-NNN (record mode)
brief next todo                     # works for any type
```

## Code + Doc Search

```bash
brief query "<symbol or keyword>"          # code symbols + docs — shows callees & callers
brief query --full "<symbol>"              # full exploration: source code, all edges, usages, impact
brief query --full --json "<symbol>"       # structured JSON with everything
brief query --impact "<fn>"                # blast radius of a change
brief query --json "<q>"                   # structured JSON output
```

**Base output** always shows callees (what it calls) and callers (what calls it) for each match.
**`--full`** adds: source code, all edge types, usages, impact — equivalent to `codegraph explore`.

Use `brief query` as the **default lookup** — it covers both code and docs.
Use `brief query --full` when you need deep exploration of a symbol (reviewing, debugging, impact analysis).
Only use `brief search` when you specifically need doc-only results.

## Graduated Context

```bash
echo "body" | brief context graduate "title"   # save cross-cutting knowledge
echo "body" | brief context graduate "title" --source=skill/implement
brief context list                             # see all graduated context
brief context "<query>"                        # search graduated context
```

Graduate context when you discover knowledge that applies across features,
would be lost if only in conversation, or future agents need to know.

## If CLI is not available

Fall back to reading files directly:
- Canonical Markdown records when `.brief/records.json` exists; generated views may be stale
- `documentation/tracker.yaml` — legacy authority only without the marker
- `documentation/memory/` — individual memory files

## When to check

SDLC skills specify exactly when. General principle: **before starting work, check what the
project already knows** about the area you're touching.

## Mandatory concurrent storage and installation rules

Read the installed Brief `references/records-and-installation.md` contract for record/install work.
In record mode, mutate individual canonical records through the CLI; preserve `_brief` metadata.
New story IDs are feature-scoped (`checkout/S-001`), tasks `checkout/S-001-T1`; use returned IDs.
Keep generated tracker.yaml/PROJECT-TRACKER.md local and ignored; never routinely commit them.
Never edit monolithic log.md/logs.md or existing entries. Use `brief log add` with session/agent
metadata for a new unique tracked file each time. Run `brief verify-records --base=<base>` during
verification/review; failures block readiness. Same-record collisions require explicit resolution.
Recommend tracked local `.brief/workflow/` packages for teams. Global installation is a separate
machine choice. Respect the selected scope; `brief update --dry-run` precedes explicit updates.
Preserve local customizations; do not silently refresh pinned project copies or delete foreign files.
