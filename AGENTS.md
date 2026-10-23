# Repository Guidelines

## Project Structure & Module Organization

This is a local-first Python application built with Streamlit. `app.py` contains the UI, image scanning, SHA-256 and pixel hashing, perceptual matching with a BK-tree, and quarantine/restore operations. `requirements.txt` declares Streamlit, Pillow, and ImageHash dependencies; `README.md` documents setup and the review workflow.

Runtime data lives beside `app.py`: `dedupe_cache.sqlite3` caches scan results, and `review_decisions.json` records actions. Images come from a user-selected folder; there is no bundled assets directory or test suite.

## Build, Test, and Development Commands

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. No separate build step is configured. Run `python -m py_compile app.py` for a syntax check; it does not validate application behavior.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and uppercase names for constants such as `DB_PATH`. Prefer `pathlib.Path` for path handling and parameterized SQLite queries. Keep helpers focused and separate filesystem operations from UI rendering where practical. No formatter or linter is configured. Use Streamlit's `width="stretch"` or `width="content"` rather than deprecated `use_container_width`.

## Testing Guidelines

No automated testing framework or coverage threshold is configured. Validate changes using disposable image fixtures: byte-identical copies, re-encoded images, resized variants, and unreadable files. Check scanning, keeper suggestions, quarantine, restore, destination-name collisions, and per-file deletion confirmation. Never test deletion against a real photo library. If adding automated tests, place them in `tests/` with `test_*.py` names and document their runner.

## Commit & Pull Request Guidelines

This checkout has no Git metadata, so existing commit conventions cannot be verified. Use short, imperative subjects, such as `Fix quarantine destination collisions`. Keep changes focused. PR descriptions should explain behavior changes, list validation performed, link relevant issues, and include screenshots for UI changes. Obtain explicit approval before pushing, creating a PR, or merging.

## Data Safety

Preserve explicit confirmation before quarantine moves and permanent deletion. Deletion must remain restricted to quarantined files. Preserve relative paths and collision-safe destinations. Exclude personal images, SQLite caches/journals, review logs, and local configuration from commits.

<!-- brief:workflow version="0.2.0" updated="2026-10-23T05:34:10.449Z" -->

## Brief Workflow Integration

For brief work, read .brief/workflow/skills/brief/SKILL.md and the selected phase. This managed
integration replaces legacy brief ordering/tool-mapping boilerplate. Preserve custom project
constraints; surface unresolved conflicts rather than overriding them silently.

- Planning explicitly reads relevant project rules, decisions, skills, and agent guidance and
  applies them in PRD/TRD/tasks. Implementation checks current rules and follows settled choices.
- User selects strict/selective/auto per story. All modes seek clarity when ambiguity remains,
  preserve protected-operation approvals, and require explicit approval before push/PR and merge.
- Review fixes every introduced/worsened issue before publication, regardless of severity;
  existing debt is the user's choice. Retro applies authorized rules/skills/agents improvements
  before publication by default, followed by review of changes and final checks.
- Explicit urgency can defer retro with a durable owner/revision/trigger. Later changes receive
  incremental review and affected verification; a clean user test needs no repeated retro.
- Read .brief/workflow/skills/brief/references/records-and-installation.md for storage/install work.
  Use qualified feature/story IDs and canonical records; keep generated trackers local. Never edit
  historical monolithic logs or existing entries; use `brief log add` for new session/agent files.
  Run `brief verify-records --base=<base>` during verification and resolve violations before readiness.
  Respect pinned project packages and explicit global/local update scope; preserve customizations.
- Capture scoped choices immediately in the current repo's knowledge store. Use brief memory
  for canonical documentation/memory files and MEMORY.md index; no provider-global memory store.
- If named QA/reviewer/self-improving agents are unavailable, follow the same source procedures
  directly: .brief/workflow/agents/. Run project-required checks; missing required checks are blocked,
  while genuinely inapplicable checks are N/A. Never claim an unavailable check passed.

Shared workflow rules: .brief/workflow/rules/brief-lifecycle.md and
.brief/workflow/rules/git-workflow.md. Read applicable project rules explicitly on every provider.
For migrations, schema changes, or destructive data operations, also read
.brief/workflow/rules/db-safety.md before preparing or running commands.

The tracked project bundle takes precedence over machine-global Brief skills.

<!-- /brief:workflow -->
