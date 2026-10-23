# Apply Project Knowledge Before Design and Execution

Before PRD/TRD/tasks, read [records and installation](records-and-installation.md). Apply the actual
project's selected install scope, record authority and qualified IDs; preserve immutable logs and
pinned packages. Reuse settled choices and resolve any genuinely open choice before dependent work.


Use during PRD, TRD, task planning, implementation, and review. Resolve context before asking
questions already answered by the user or project. Keep retrieval targeted to the proposed work.

1. Read project AGENTS.md and relevant provider/project guidance. Inventory rules for anticipated
   code paths, including naming, database design, architecture, tests, and deployment. Explicitly
   read applicable rules even while editing a Markdown plan; do not rely on host path activation.
2. Search decisions, memory, and previous retros: `brief search "<area>"`, `brief memory list`,
   `brief memory show <slug>`, and relevant context. If tools are unavailable read the repo's
   MEMORY.md and knowledge files. A short index is not the complete memory inventory.
3. Read applicable choices and their source/scope/status. Current explicit user instructions apply
   at their stated scope. Superseded records are history; observations are not user-approved rules.
   Do not expand a feature exception to the project or silently reconcile unresolved conflicts.
4. Inspect the actual implementation and tests. Code establishes facts; it does not revoke a user
   preference merely by violating it. Ask about conflicts that remain unresolved after investigation.
5. Record an **Applied Constraints** table in the PRD/TRD/plan as appropriate:

   | Source | Scope/status | Effect on this design or task | Verification / unresolved choice |
   |--------|--------------|-------------------------------|----------------------------------|

   Include only relevant constraints with their concrete effect; do not dump a rule catalog.
   If none apply, state what was checked. Do not invent preferences to fill the table.
6. Resolve known product/design questions before execution. Inline actionable decisions, rationale,
   naming/schema examples, relevant rules, and verification in tasks so a fresh agent can execute.
   Link sources for provenance. Record planned critical/manual checkpoints for mode recommendation.
7. Recheck current applicable rules at implementation/review time. Follow settled choices without
   re-asking; genuinely changed conditions or ambiguity require clarification before dependent work.

Capture new explicit choices immediately using [memory](../memory/SKILL.md). Retro and curation
continue to improve rules, skills, and agent instructions; planning must consume that output.
