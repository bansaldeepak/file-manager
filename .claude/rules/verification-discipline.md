---
description: Absence ≠ proof, unfailable checks, trace before attributing. Hard-won verification rules.
---

## Verification Discipline

- **Absence ≠ proof** — A grep returning nothing proves the pattern wasn't found, not that the thing doesn't exist
- **Unfailable checks look like passing ones** — Every guard needs a negative test proving it goes red
- **Task claims are unverified** — Check every assertion about code against the actual codebase before implementing
- **Trace before attributing** — Measure localises a symptom; trace the call path before blaming a component
- **Ask fix-now-vs-defer** — Don't silently punt when testing surfaces a gap in the story's blast radius
- **Self-contained specs for handoff** — Inline code context, schema, decisions. A link is not context.
