---
name: implement
description: "Execute approved stories with user-selected strict, selective, or auto commits; handle ambiguity, checks, resume state, and final publication approval."
user_invocable: true
model: opus
---

# /brief implement — Story Execution

The [router](../SKILL.md) owns phase order; this phase owns mode selection, commits, and publication.
Read the story, requirements, project instructions, and [planning context](../references/planning-context.md).
A mode changes approval frequency, not scope, requirements, checks, or protected-operation authority.

## Start or Resume

1. Inspect Git status and branch. Resolve the actual default/base from project instructions or Git
   metadata. Branch out before edits if on the base; preserve unrelated work and use the story branch.
2. Confirm story.md, summary.md, and tasks exist. Preserve legacy tasks.md/tasks/index.md formats.
3. Read [record/log rules](../references/records-and-installation.md), then the story risk/verification summary and relevant tasks, rules, and code. Resolve missing
   facts before recommending auto.
4. Recommend a mode with evidence; ask the user to select unless they explicitly already did.
   Record selection and source in story.md. A recommendation or silence is not consent.
5. On resume reuse the selection for this story, reconciling Git/task state and outstanding gates.
   A saved mode does not answer an open question or extend to a new story.

| Mode | Local commits | Human checkpoints |
|------|---------------|-------------------|
| strict | Approval before each commit, including bookkeeping, review fixes, and retro | Every commit with a concrete verification point |
| selective | Automatically commit verified routine work | Before committing critical changes and at planned human/browser checkpoints |
| auto | Complete authorized tasks, fixes, checks, and local commits | End-of-story report before publication; ambiguity/protected actions still pause |

Recommend **selective** for migrations/data transformations, auth/permissions, consent/payments,
breaking external contracts, or human browser checks. Group checks around completed flows; a flow
may span routine commits, but keep verification pending until actually checked. Recommend **auto**
for clear code-only work with adequate automated verification and no critical/manual checkpoints.
Recommend **strict** for requested granular oversight or weak verification. Weak evidence never
authorizes guessing.

The user chooses. Explain new risks and recommend a mode change without silently changing it.
Reuse existing explicit approval for concrete changes at its stated scope; selective mode does
not require asking for the same critical decision again.

Record in story.md (ordinary Markdown; no tracker schema change needed):

```text
Execution mode: strict | selective | auto
Selected by: <explicit user instruction and date>
Recommendation: <risk and verification evidence>
Retro timing: before publication | explicitly deferred (<reason/owner/trigger>)
Critical/manual checkpoints: <task or completed flow and evidence>
Open questions/approvals: <none or unresolved items>
```

Offer retro-first (default) and urgent deferral when selecting execution policy. Reuse a timing
choice already made; a mode alone does not authorize deferral.

## Ambiguity — All Modes

Inspect approved plans, choices, rules, and code first. If intended behavior or scope remains unclear,
explain the concrete uncertainty and options, recommend if justified, and ask. Pause dependent edits,
commits, and operations until answered; independent work may continue. Confidence, timeouts, and
silence are not answers. Do not re-ask settled questions. Capture the answer and update affected
requirements, decisions, tasks, and tests before resuming. A wrong spec is a finding, not permission
to silently reinterpret the task.

## Task Loop

1. Pick the next unblocked task; verify branch/current constraints and mark it in progress.
2. Implement approved behavior. Capture explicit user choices immediately via [memory](../memory/SKILL.md).
3. Sync affected docs; run the project's required checks using QA or the same commands directly.
   Run `brief verify-records --base=<story-base>` for Brief-managed changes; do not commit tracker views or edit historical logs.
   Checks established as inapplicable are N/A; a missing required command or unavailable required verification is blocked, never passed.
4. Fix clear failures inside approved scope and rerun relevant checks. Never weaken assertions or
   bypass hooks. For pre-existing failures, provide baseline evidence and request fix/defer disposition;
   do not silently waive a required check.
5. Apply the mode's commit gate. One task = one implementation commit. Give concise progress updates
   for automatic commits; use the checkpoint report when human action is required.
6. Update status, acceptance/result evidence, and summary; commit bookkeeping separately under the
   same mode. Verify the actual status field, not just checked boxes.
7. Continue. Distinguish implemented/committed from reviewed, verified, published, or merged.

Use the project's vocabulary: the brief CLI uses `brief story task update <task> status=done`
for finished tasks. Preserve legacy formats rather than migrating during execution. Report actual
commit counts including bookkeeping.

## Human Checkpoint

```text
Task/checkpoint: <ID and completed flow>
Changed: <what and why>
Checks: <commands/results/limitations>
Verify: <URL/click path or files and expected result>
Risk: <data/migration, auth/payment, contract/env changes, deletions, or none>
Requested approval: <specific commit or protected operation>
```

Prepare reviewable work before asking. Approval to write/commit a migration is not approval to run
it: read and follow the [DB safety rule](../../../rules/db-safety.md), including for local/test
databases. No mode waives destructive/deploy controls.

## Finish Locally, Then Publish

Hand off automatically through the router to [pr-review](../pr-review/SKILL.md). Resolve every
introduced/worsened finding, run retro by default, review its changes, and run final verification.
Review/retro commits retain the selected mode. Deferred retro needs a durable obligation first.

Keep summary.md evidence identifying base and candidate HEAD (or tree plus pending files), commands,
human checks, finding dispositions, and limitations. The candidate must match the evidence at
publication. Inspect record-only bookkeeping diffs without repeating unrelated tests.

```text
Story: <ID, completed tasks, actual commits>
Review: <base/candidate; new findings resolved; user dispositions for existing debt>
Retro: <complete or explicitly deferred with owner/trigger>
Verification: <actual results and preview-only gaps>
Changes since human verification: <impact and retest needed>
Push triggers: <known CI/deploy behavior>
Approve push and opening/updating PR against <base>?
```

No push or PR without explicit approval for the presented changes. A combined approval is valid
when both actions were named; never infer merge approval. Preview-only checks must be disclosed
before push and completed before merge. If content changes after approval, refresh affected evidence
and approval for the changed scope. A successful user test without changes permits direct user merge.

For later changes run incremental review, relevant checks, and any affected human flows; broaden
review when architecture/contracts/shared behavior invalidate earlier assumptions. Add only new
retro learnings. If already merged, use a fresh branch from current base and linked follow-up through
normal gates; never replay merged commits or resurrect a merged PR.

## Invariants

- No direct base commits, force-push, or hook bypass without explicit applicable authorization.
- Unanswered gates stay open; modes never expand scope or learned preferences.
- Required checks and all introduced/worsened findings must be resolved before publication.
- Reuse valid choices and approvals; ask about unresolved or changed conditions.
