---
name: plan
description: "Story-Based Planning Skill. Interactive planning for breaking features into tracked stories and tasks."
user_invocable: true
model: opus
---

# /brief plan -- Story-Based Planning Skill

Interactive planning skill for breaking features into tracked stories and tasks.

**Usage**: `/brief plan <feature description>`

## Instructions

Before drafting, follow [planning context](../references/planning-context.md). Explicitly apply relevant user decisions, rules, skills, and agent guidance; record an Applied Constraints table with their effect. Resolve known questions before execution and capture new choices immediately via [memory](../memory/SKILL.md).

You are entering planning mode. Do NOT write any implementation code. Your job is to produce a story with tasks that will guide implementation.

### Phase 0a: Branch Check

Run the branch check from `plan`'s router before creating any story files. You should already be on
the feature branch from `prd`/`trd` — if `git branch --show-current` prints `main`, branch out now
(`feature/<slug>`, matching what Phase 4 will write into `story.md`).

### Phase 0: Ensure PRD/TRD Exist

**Every feature folder must have both `PRD.md` and `TRD.md`.** No exceptions — we don't skip steps.

Before planning, check `documentation/stories/<feature-name>/`:

1. **PRD.md**:
   - If it exists and is approved (🔒) → reference it as the source of truth for scope
   - If it exists but is not approved → stop and redirect: "PRD needs approval first. Run `/brief prd` to finalize."
   - If it doesn't exist → create it. For non-trivial features, run the full `/brief prd` flow. For trivial work (bug fixes, config changes), create a minimal PRD with skip justification:

   ```markdown
   # PRD: <Feature Name>

   **Status**: skipped
   **Reason**: <Why full PRD is unnecessary — e.g., "Single bug fix with clear reproduction steps", "Config change with no user-facing impact">

   ## What
   <One-sentence description of the change>
   ```

2. **TRD.md**:
   - If it exists → reference it for architecture decisions and implementation order
   - If it doesn't exist → create it. For arch changes, run the full `/brief trd` flow. For work with no arch impact, create a minimal TRD with skip justification:

   ```markdown
   # TRD: <Feature Name>

   **Status**: skipped
   **Reason**: <Why full TRD is unnecessary — e.g., "No new services, schemas, or architectural patterns introduced">

   ## Approach
   <One-sentence summary of implementation approach>
   ```

### Phase 1: Gather Context

**Check project history first.** Before planning tasks, surface what the project already knows.

**Primary** — if `brief` CLI is installed (`which brief`):
```bash
brief search "<feature keywords>"
brief status
```

**Fallback** — if CLI is not installed, read files directly:
- Canonical story/item Markdown in record mode; CLI views are current. Generated tracker views may be stale.
- Legacy `documentation/tracker.yaml` only when no record-authority marker exists.
- `memory/` files — prior learnings, constraints, gotchas for this area
- Recent retro files (`documentation/stories/*/retro.md`) — what went wrong in similar past work

Look for: open TODOs this story might resolve (link them in tracker), prior decisions (constraints),
retro findings (patterns from similar past work).

**Why this matters:** A story that re-solves a problem a retro already diagnosed, or ignores a
TODO that's already tracked, wastes effort. Prior findings are planning inputs.

Then read:
- **PRD.md and TRD.md** (always present — created in Phase 0)
- Project AGENTS.md (or CLAUDE.md/GEMINI.md) and documentation/rules/
- Database schema (prisma/schema.prisma if it exists)
- Existing modules/components related to the feature
- Any referenced docs, decision docs, or requirements

### Phase 2: Requirement Gathering (PM Hat)

Before discussing *how* to build anything, understand *why* and *what*. This is mandatory.
If a PRD exists, use it as the foundation — don't re-ask questions already answered there.

**Step A -- Why**: What problem does this solve? Who is affected? Cost of inaction?
**Step B -- What**: What changes from the user's perspective? Success criteria? Explicitly out of scope?
**Step C -- Clarifying Questions**: Check approved requirements and applicable guidance first. Ask only unresolved questions about scope, behavior, architecture, edge cases, or risk. Do not invent a question quota or repeat settled choices.

For **tech upgrades**: also ask about migration path, rollback plan, incremental approach.

**Wait for answers to genuinely unresolved questions before dependent planning.**

### Phase 3: Propose Breakdown

Based on answers, propose:
- Story title and goal (one sentence)
- Acceptance criteria (checkboxes)
- Ordered task list with task ID, description, files to create/modify, dependencies

**Documentation impact analysis** -- For each task, assess whether the change affects how the project is understood. If any task introduces new patterns, configs, commands, or conventions, include a doc sync step.

**Vendor-primitive risk check** -- For each task, ask: does this task's design *depend on* a specific
behavior of a third-party vendor/SDK primitive (an auth provider's reverification semantics, a
payment provider's webhook ordering, a specific API's rate-limit or retry behavior, etc.) that is
described in docs but not something you've confirmed hands-on in *this* codebase? If yes, that
dependency is a distinct risk tier from ordinary implementation risk — vendor docs describe intent,
not always actual behavior, and a wrong assumption here is usually only found by building the whole
feature first. Split out a small, cheap spike task ("confirm X actually behaves as Y with a minimal
reproduction") ahead of the full-build task, rather than folding the discovery into the build itself.
(Learned from experience: two full build-then-revert cycles resulted from building features whose
core design depended on a vendor primitive that didn't work as its docs described. A 30-minute spike
each would have caught it first.)

**Wait for user approval or adjustments before proceeding.**

### Phase 4: Create Story Files

**Primary** — if `brief` CLI is installed:
```bash
brief story create "<title>" --description="<context>" --feature=<folder> --branch=feature/<name>
# Then for each task:
brief story task create S-NNN "<task title>" --priority=P0 [--blocked-by=S-NNN-TN]
```
Use the returned ID (for example, `feature-name/S-001`) in all task commands. This creates the canonical story, summary and tasks directory; legacy mode also updates its tracker.

**Fallback** — create files manually following templates below.

Read [record authority and IDs](../references/records-and-installation.md). In record mode, use CLI
allocation within the selected feature; do not guess IDs or hand-create metadata. Without CLI access,
restore the CLI before record-mode mutations. For legacy projects only, preserve existing global IDs
and file formats. Choose an existing feature folder for related work or a new safe feature slug.

#### `documentation/stories/<feature-name>/S-NNN/story.md`

```markdown
# S-NNN: <Title>

**Status**: planned
**Branch**: feature/<name>
**Created**: <today's date>

## Context
<Why this work is needed>

## Goal
<One sentence outcome>

## User Story
As a <role>, I want <capability>, so that <benefit>.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Scope
**In scope:** ...
**Out of scope:** ...

## Risk and Verification
<Per-task critical changes, completed browser flows, automated coverage and evidence gaps; input to mode recommendation.>

## Execution Policy
<Selection is made by the user at implementation start; never pre-approve a mode during planning.>

## References
<Links to relevant docs, schema, requirements>
```

#### `documentation/stories/<feature-name>/S-NNN/tasks/T-001.md` (one per task)

Each task file is self-contained and tracks its own status. No separate index file needed —
task status lives in the task file's frontmatter (`Status: pending` → `done`).
For projects using external PM (GitHub Projects, Linear), status syncs there instead.

Each task gets its own file with full detail. **Each task spec must be self-contained.** Assume the executing agent (Sonnet, Codex, Gemini, or a fresh Claude session) has ZERO context from the planning conversation. The task spec is the only brief they receive.

```markdown
# S-NNN-T1: <Title>

**Priority:** P0/P1/P2 (append **-spike** if this task exists only to confirm a vendor primitive's
actual behavior before a dependent build task starts, e.g. `P0-spike`) | **Status:** pending | **Blocked By:** --

## What
One-paragraph description of the deliverable. Be specific: name the function, the file, the behavior.

## Why
Why this task exists -- what breaks or is missing without it. Include the user-facing impact.

## Context
Background a fresh agent needs to understand this task. Include:
- Current state of the code (what exists today, what's broken)
- Relevant schema/type definitions (inline the key fields, don't just reference)
- Applicable user decisions and rules: inline concrete design/naming constraints, rationale, scope, and source
- Key decisions from review (e.g., "CEO review decided X because Y")
- How this task connects to adjacent tasks (what came before, what comes after)

## How

**Step 1 -- <action>:**
- File: `exact/path/to/file.ts`
- What to change: <specific description with line references if modifying existing code>
- Code: <code block showing the implementation or pattern to follow>

**Step 2 -- <action>:**
- File: `exact/path/to/file.ts`
- What to change: <specific>
- Code: <code block>

**Step N -- Verify:**
```bash
<exact verification commands — not "run tests" but the specific test command>
```

## Files to Read First
List of files the executing agent should read before starting (gives them the context they need):
- `path/to/file.ts` -- <why: "contains the function you're modifying">
- `path/to/schema.prisma` -- <why: "StudentObjectState model definition">

## Acceptance Criteria
- [ ] Specific, testable criteria (not vague like "works correctly")
- [ ] Concrete: "typecheck passes", "returns 201 with body matching schema"
- [ ] Include the verification command for each criterion
```

**Self-containment checklist (verify before finalizing each task):**
1. Can a fresh agent execute this task by reading ONLY this file + the files listed in "Files to Read First"?
2. Are all architectural decisions explained inline (not "as discussed" or "per the review")?
3. Are exact file paths provided for every create/modify operation?
4. Are code snippets complete enough to implement from (not just "follow the pattern")?
5. Is the verification step a concrete command, not a vague instruction?
6. If this task depends on a prior task's output, is that output described (not assumed)?
7. **Does this task claim anything about another story?** "Unblocks S-NNN", "S-NNN depends on
   this", or any quote of another story's acceptance criteria — open that story's `tasks/` and
   confirm it, then name the specific task (`S-NNN-T3`), never the story alone. Reviewers read what
   a task *does*; almost nobody re-reads what it *claims about someone else's plan*, so these
   survive review and then send someone to "fix" work that was already correct.
8. **Does this task assert something is untested, missing or unhandled?** Grep before writing it.
   "An untested N-line move" and "no coverage exists for X" are claims about the repo, and they are
   the ones most often wrong. A task can be worth doing for a reason other than the one you gave —
   but then the stated reason is fiction, and a reviewer may cut the task on it.

What makes a good "How" section:
- **File paths** -- Exact paths for files to create or modify
- **Code snippets** -- Complete enough to implement from, not just hints. Include function signatures, key logic, types.
- **Inline context** -- Don't say "follow the pattern in X." Show the relevant 10-20 lines from X right here.
- **Verification commands** -- `npm run typecheck`, `npx vitest run --config vitest.unit.config.ts test/unit/tutor-engine/post-session.test.ts`, specific curl commands
- **Edge cases** -- Note error handling, constraint violations, auth checks
- **Schema/type info** -- Inline the relevant Prisma model fields or TypeScript types. Don't make the agent hunt for them.

**File naming:** `T-001.md`, `T-002.md`, etc. (zero-padded for sort order)

**Context efficiency:** Read the current task plus its required constraints/read-first files. Mode selection uses the story risk summary; inspect other task specs when missing risk evidence or dependencies require it.

#### `documentation/stories/<feature-name>/S-NNN/summary.md`

```markdown
# S-NNN: <Title> -- Summary

## What Changed
<Updated after each task is completed>

## Decisions Made
<Non-obvious choices and why>

## Testing
<Automated coverage the story adds or relies on. Leave the manual-verification line as
`<planned verification; evidence pending>` — identify expected browser/critical checkpoints during planning and reassess during execution. Do not claim a future check passed.>

## Follow-up
<Deferred items, future improvements>
```

### Phase 5: Verify Project Tracker

Phase 4 already created the story/tasks. Verify their IDs, statuses, dependencies, and links using
`brief story show <story>` and `brief story tasks <story>`. Update existing records if needed; do not
create the same story/tasks again. With no CLI, inspect the existing tracker and files directly.

### Phase 6: Confirm

Report back:
- Story ID and title
- Number of tasks
- Branch: `git branch --show-current` — confirm it matches `story.md`'s **Branch** field, not `main`
- Recommend an execution mode using the story risk/verification summary; obtain selection unless explicitly supplied. Preserve the user's authorization to start, rather than asking again.

Also create Claude Code tasks (TaskCreate) mirroring the story tasks for session visibility.

## Status Values

- **draft** -- Initial idea, not yet broken down
- **planned** -- Broken down into tasks, ready to start
- **in_progress** -- Actively being worked on
- **blocked** -- Waiting on dependency
- **completed** -- Done, committed, verified

## Legacy Format Handling

Existing stories may use older formats. When working with an existing story:

1. **Detect format** — Check whether `S-NNN/tasks.md` (legacy single-file) or `S-NNN/tasks/index.md` (legacy split) exists
2. **Legacy story** — Continue using the existing format for that story. Do NOT migrate mid-execution — finish the story in its original format
3. **New stories** — Use individual `tasks/T-NNN.md` files with status in frontmatter. No `index.md` needed — task files self-report status
4. **Same for PRD/TRD** — If a feature folder predates mandatory PRD/TRD, don't retroactively create skip-justified files for completed stories. Only enforce for new work in that folder.

## Rules

- Never write implementation code during planning
- Always check for unresolved questions; proceed without repeating answers already established
- Always wait for user approval of the task breakdown
- Tasks should be ordered so each builds on the previous
- Each task should be completable in a single commit
- If a task feels too large, split it further
- Every story must account for documentation sync
- **Self-contained tasks are non-negotiable.** Each task spec will be executed by a fresh agent (Sonnet, Codex, Gemini) with no prior context. The task file IS the entire brief. If executing the task requires knowledge not written in the task file, the task spec is incomplete. Never assume shared context from the planning session.
- **Inline over reference.** Don't write "see the TRD for architecture decisions." Copy the relevant decision into the task spec. Don't write "follow the pattern in X." Show the pattern. The executing agent may not have access to the planning conversation or review documents.
- **Verify every claim about another story against that story's `tasks/`, including when correcting
  one.** A cross-story claim is the one thing planning review reliably misses — it reads each task's
  content, not its assertions about a neighbour. Cite the specific task ID. When you later find such
  a claim wrong, re-check it the same way before writing the correction: a wrong correction sends
  someone to edit a plan that was already right, which costs more than the original error.
- **Review decisions must be in task specs.** If a CEO/eng review made a decision that affects implementation (e.g., "use separate queues, not shared queue"), that decision and its rationale must appear in the task spec that implements it.
