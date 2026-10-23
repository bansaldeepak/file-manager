---
name: memory-review
description: "Reconcile captured choices, preserve inactive context, and curate authorized rule, skill, agent, and memory improvements."
user_invocable: true
---

# /brief memory-review — Curation

Read [memory](../memory/SKILL.md) for storage, scope, and mutation contracts.

Follow [record/log rules](../references/records-and-installation.md): use individual records and new
immutable log entries; preserve canonical metadata and keep generated views out of routine commits.

1. Inventory the canonical store, including entries absent from the short index. Collect the active
   conversation's explicit choices from the caller, plus relevant decisions and retro findings.
2. Flush inactive feature context to its context.md; retain index/discovery pointers as needed.
   Do not prune user preferences merely because the feature ended.
3. Invoke self-improving with inventory, captured choices, sources, scope, and existing edit
   authorizations. If unavailable, follow its procedure in the active agent.
4. Apply authorized improvements and verify source/destination/recall. Missing promotion approval
   requires a concrete proposal; existing scope-specific approval is reused.
5. Report captures, applied/promoted/extracted items, proposed items, supersessions/retirements,
   conflicts, and before/after accounting. Use the current story's commit policy.

Do not silently enlarge scope or remove facts. Unresolved conflicts and unapproved promotions
stay explicit; curation is not permission to change project policy independently.
