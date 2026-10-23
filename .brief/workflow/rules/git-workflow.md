---
description: Git branch safety and commits under explicitly selected brief execution modes.
---

# Git Workflow

Check branch and worktree before edits. Use feature|fix|chore|hotfix/<slug>, not the actual default/base
branch. Preserve unrelated changes. Resolve the base rather than assuming main.

Commit authority follows the user's explicit scope. Brief implement records strict (approve every
commit), selective (verified routine commits; critical/manual gates), or auto (authorized local story
commits). This covers bookkeeping, review fixes, and retro. Without a mode or other explicit commit
authorization, ask before committing. Reuse valid approval; silence is not consent.

Review and fix all introduced/worsened findings before publication. Retro precedes publication unless
explicitly deferred; review its changes and verify the resulting candidate. Push/PR needs explicit
approval for the presented changes in every mode; merge is separate. No force-push or hook bypass
without explicit applicable permission. An unanswered gate remains open.

```text
type(scope): subject

Task: S-NNN-TN
```

Types: feat, fix, refactor, docs, test, chore, style, perf, ci.
One task = one implementation commit; bookkeeping separately. Later changes need review and
verification of affected scope.
