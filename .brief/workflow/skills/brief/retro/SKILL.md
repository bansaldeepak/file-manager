---
name: retro
description: "Capture story learning and complete authorized rule, skill, agent, and memory improvements before publication; handle explicit deferral and incremental follow-ups."
user_invocable: true
model: opus
---

# /brief retro — Learning Before Publication

The [router](../SKILL.md) owns timing: normally after local review fixes and before final
verification/publication. Do not wait for a PR or preview test to capture known implementation
learnings. Preview/production outcomes remain pending until observed.

For a standalone BUG without a story, use its bug record, reproduction, fix, and review evidence;
append the retrospective to that record through the bug CLI. Do not invent story artifacts.
The ordinary commit/publication controls still apply.

Follow [record/log rules](../references/records-and-installation.md): use individual records and new
immutable log entries; preserve canonical metadata and keep generated views out of routine commits.

## Gather and Reconcile

Read requirements, story/tasks in their existing format, summary/review evidence, decisions, and
choices captured from the conversation. Compare planned/delivered scope, surprises, rework, and
planning/check gaps. Inspect actual branch history; reachability from the base after merging does
not prove someone committed directly to it.

Use [memory](../memory/SKILL.md) to reconcile choices. The active agent supplies relevant conversation
decisions to curation; a curator cannot recover unseen turns. Capture omissions with source, stated
scope, and supplied rationale. Never invent alternatives, motives, or successful outcomes.

## Improve the System

Identify each learning's destination: decision, memory, project rule, skill, or agent instruction.
Preserve the existing improvement loop: apply authorized edits and verify their destinations.
Recording a suggestion alone is not completion.

Reuse explicit approval within its scope. Where authorization is missing, propose concrete edits
and ask, especially before broadening feature choices to project/shared policy. Execution mode is
not promotion approval. Keep unapproved/explicitly deferred optional improvements visible; do not
defer confirmed defects introduced by the story.

Run [memory-review](../memory-review/SKILL.md), invoking self-improving when available or following
its procedure directly. Its results must feed future PRD/TRD/tasks as well as implementation.

## Record Completion

Write retro.md beside story.md, under 100 lines:

```text
Story and covered revision:
Timing/status: complete | deferred | incremental
Planned vs delivered:
What worked / what did not:
User choices captured: <source/scope/destination>
Learnings: <evidence/action/destination/completed or pending>
Rules/skills/agents updated: <authorization and verification>
Memory curation: <captured/promoted/superseded/retired/unresolved>
Pending observations/follow-up: <owner and trigger>
```

Update tracking truthfully: retro complete does not mean published, user-tested, or merged.
Commit retro/curation under the selected mode, separately from implementation. Return to the
router for review of changed artifacts and final checks; retro cannot bypass publication gates.

## Urgent Deferral

Only defer when the user explicitly selects publication first. Review/fixes, checks, and publication
approval still apply. Before publishing, create a durable follow-up linked from story and PR summary:
status deferred, user consent/reason, owner, covered revision, and completion trigger. Preserve
already-captured choices immediately. Surface pending learning on next relevant resume; do not
promise unattended execution without an actual worker/scheduler.

- PR open: analysis may run while the user tests; isolate concurrent edits. Review/check additions
  before obtaining applicable commit/push approval and explain any required retest.
- PR merged: fresh branch from current base and linked follow-up through normal gates. Preserve
  unpublished work without replaying already-merged implementation commits.
- Merge race: recheck PR state before publication and choose the appropriate path.

## Incremental Retro

After publication record only new findings, decisions, outcomes, and prevention measures. Review
changed content and rerun affected checks/human flows; broader behavior changes may need full review.
Successful user testing with no changes/new learning permits direct user merge; do not force another
retro or a bookkeeping-only commit.
