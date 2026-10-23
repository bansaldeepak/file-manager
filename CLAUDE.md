

<!-- brief:workflow version="0.2.0" updated="2026-10-23T05:34:10.487Z" -->

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

## Design System

Read DESIGN.md before visual or UI work: it defines the fonts, colors, spacing, and
aesthetic direction. Ask the user before departing from it. When reviewing or QA-ing
UI, flag code that doesn't match DESIGN.md.
