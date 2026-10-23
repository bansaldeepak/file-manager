---
name: bug
description: "Bug mini-workflow: triage, risk-assess, fix, qa, close. Invoke via /brief bug."
---

# /brief bug — Bug Mini-Workflow

Structured bug handling: record → assess → fix → verify → close. One invocation, full lifecycle.

**Usage**: `/brief bug "description of the bug"`

## Phase 1: Record

Create the bug in the tracker:
```bash
brief bug create "<description>" --body="<details if provided>"
```

Note the returned BUG-NNN ID. This is your tracking reference for the rest of the workflow.

## Phase 2: Triage

Assess the bug:
- **Severity**: critical (system down) | major (feature broken) | minor (cosmetic/edge case)
- **Priority**: P1 (fix now) | P2 (fix this sprint) | P3 (backlog)
- **Blast radius**: What else could this affect?

Update the bug record:
```bash
brief bug update BUG-NNN severity=<level> priority=<level>
```

## Phase 3: Risk Assessment (conditional)

**Auto-trigger** when the bug fix touches ANY of:
- Database migrations or schema changes
- Authentication or authorization logic
- External dependencies (third-party APIs, webhooks)
- Payment or billing flows

**If triggered**, run this assessment:

> Imagine this fix has been deployed. It made things worse. What went wrong?

Evaluate from 4 angles:
1. **Technical**: What could this fix break? Race conditions? Edge cases?
2. **Product**: Could the fix have unintended UX consequences?
3. **Process**: Is there a simpler/safer approach we're not considering?
4. **External**: Anything outside our control (third-party behavior, timing)?

Categorize each risk:
- `blocks-fix` — Must be mitigated before committing. State the specific mitigation.
- `acceptable` — Acknowledged risk, acceptable for this fix. No action needed.

If ANY risk is `blocks-fix`: address the mitigation before proceeding to Phase 4.

**If NOT triggered** (simple bug, low blast radius): skip directly to Phase 4.

## Phase 4: Fix

1. Check branch and worktree; branch out if on the actual default/base branch. Resolve ambiguous intent before edits.
2. Implement the fix.
3. Keep changes minimal — fix the bug, don't refactor adjacent code.

## Phase 5: Verify

Run the project-configured checks using QA or directly; inapplicable checks are N/A; missing or unavailable required checks block readiness. Verify affected browser flows when needed.

## Phase 6: Close

1. Use the linked story's explicit execution mode for commits, or ask for commit approval if none exists:
   ```
   type(scope): subject

   Task: BUG-NNN
   ```
2. Update tracker:
   ```bash
   brief bug update BUG-NNN status=done
   ```
3. If the bug revealed a systemic issue: create a TODO for the underlying problem
   ```bash
   brief todo create "Address root cause of BUG-NNN" --body="..."
   ```

Use the bug record for review/retro/publication evidence when there is no linked story. Append
review and retrospective sections through the bug CLI; do not invent story files to complete a handoff.

Before push/PR, hand off through the [router](../SKILL.md) for [review](../pr-review/SKILL.md), retro by default, final checks, and the [publication gate](../implement/SKILL.md). Fix all introduced/worsened findings; existing debt remains the user's choice.

## Escalation

If during investigation the bug turns out to be a feature gap (not a defect):
1. Update bug: `brief bug update BUG-NNN status=escalated`
2. Create a story: `brief story create "..."`
3. Link: `brief bug update BUG-NNN escalated_to=S-NNN`
4. Exit this workflow — the story follows the full SDLC lifecycle.

## Rules

- Always record first (Phase 1), even if the fix is obvious
- Never skip risk assessment when auto-trigger criteria match
- One bug = one commit. Don't bundle unrelated fixes.
- Commit authority follows an explicitly applicable story mode or direct approval; no implicit push/merge consent.
