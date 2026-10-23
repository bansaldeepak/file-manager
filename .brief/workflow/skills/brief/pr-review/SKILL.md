---
name: pr-review
description: "Review local changes before push or PR; classify finding origin, resolve all introduced issues, and re-review later changes with current evidence."
user_invocable: true
model: opus
---

# /brief pr-review — Before Publication

Run automatically during authorized story execution before push/PR, and for later changes before
another publication or merge. [Router](../SKILL.md) owns transitions;
[implement](../implement/SKILL.md) owns commit/publication approval. This phase does not publish.

For a standalone bug, use the bug record/reproduction as scope and save review evidence there;
no story/PRD/TRD is fabricated. Use direct commit approval unless a mode explicitly covers the bug.

## Scope and Context

Read project instructions, requirements/tasks, applicable rules and scoped user choices using
[planning context](../references/planning-context.md). Resolve the actual base branch. Inspect Git
status, merge-base-to-HEAD diff, staged/unstaged changes, and relevant untracked files. A committed
diff alone must not hide new content. Record base, candidate revision/tree, and included dirty files.

Read changed files and affected callers/tests, not just hunks. For incremental review identify the
previous reviewed revision and whether new changes require broader coverage. Invoke the reviewer
agent with scope, constraints, and verification evidence; if unavailable follow its procedure
directly and report the fallback.

Read [record/log rules](../references/records-and-installation.md); run `brief verify-records --base=<review-base>` and resolve violations. Check correctness, security, performance, meaningful tests, coding/naming rules, maintainability,
scope, and architecture. Do not manufacture issues or enforce personal taste as a requirement.

## Finding Contract

| Field | Required evidence |
|-------|-------------------|
| ID / location | Stable identifier, file/line and defect/reproduction |
| Severity | Critical, important, or minor; concrete consequence |
| Origin | Introduced, worsened, pre-existing, or unknown; base/history evidence |
| Resolution | Correction or user's disposition for existing debt |
| Verification | How the correction was checked and on which candidate |

Severity communicates impact; origin determines deferral authority. An existing defect made worse
or newly exposed by changed behavior is worsened. Investigate unknown origin rather than labeling
it old debt. Unsupported taste-only suggestions are advisory, not confirmed findings.

## Resolution

- **Introduced/worsened, every severity:** fix, review the correction and verify before publication.
  A minor label or a TODO is not permission to ship a confirmed new defect.
- **Pre-existing:** present findings together with severity/evidence for user fix-now/defer choice.
  Record the disposition and follow-up. Do not silently change unrelated code, waive required
  failing checks, or label deferred debt fixed.
- **Unknown:** investigate baseline/history. Keep unresolved origin visible and block the dependent
  readiness claim until resolved.
- **Requirement/scope conflict:** seek clarity before choosing new behavior or altering the design.

Correction commits follow the selected mode, including strict approvals and selective critical
checkpoints. Re-review fixes; update requirements/tasks/tests when an approved design changes.

## Report and Handoff

Save a concise record in summary.md, or link a larger review artifact:

```text
Scope: <base, candidate revision/tree, dirty/untracked files>
Constraints checked: <applicable rules and user choices>
Findings: <ID/severity/origin/evidence/resolution/verification>
Existing debt: <explicit user dispositions>
Advisory suggestions: <optional or none>
Checks: <actual results and limits>
Verdict: ready for next local phase | blocked (<unresolved items>)
```

Return to the router for retro by default, review of its changes, and final verification before
the publication gate. Do not call an unreviewed/unverified candidate ready. After publication,
explain the delta and run incremental review plus affected checks/human flows. Expand to full
review when architecture, contracts, or shared behavior invalidate earlier assumptions. Notes
need factual/scope/reference review, not unrelated browser retesting. No changes after successful
user testing require no repeated review or retro.
