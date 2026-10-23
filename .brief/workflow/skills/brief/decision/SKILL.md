---
name: decision
description: "Record a technical or product decision with trade-offs, reversibility assessment, and what we're giving up. Use anytime a non-obvious choice is made."
user_invocable: true
---

# /brief decision -- Decision Document

Records non-obvious decisions with full context so future-you (or teammates) understand why a choice was made.

**Usage**: `/brief decision <decision topic>`

**Source**: Adapted from Mehdibargach/claude-code-pm-skills decision-doc (reversibility + trade-off framework).

## When Claude Should Auto-Invoke

- During `/brief trd` when a design decision has significant trade-offs
- During implementation when an unexpected fork-in-the-road appears
- When the user asks "should we do A or B?"
- When choosing between competing libraries, patterns, or approaches
- Record an explicit decision immediately; seek the user's choice only if it is unresolved. Reuse stated approval and scope.

## Instructions

### Phase 1: Frame the Decision

Understand the context:
- What triggered this decision?
- What are the constraints (time, tech, business, compliance)?
- Who is affected?

### Phase 2: Write the Decision Doc

Save to `documentation/decisions/DEC-NNN-<slug>.md` (sequential numbering):

```markdown
# DEC-NNN: <Decision Title>

**Date**: <today>
**Status**: Proposed | 🔒 Decided | Revisited | Superseded by DEC-XXX
**Deciders**: <who made this decision>
**Source and Scope**: <user statement/date and feature/module/project applicability>
**Context**: <PRD/TRD/Story reference if applicable>

## Decision

<One sentence: what we decided>

## Context

<Why this decision came up. What problem or fork-in-the-road triggered it?>

## Options Considered

### Option A: <name>
- **Description**: <how it works>
- **Pros**: <benefits>
- **Cons**: <drawbacks>
- **Effort**: S/M/L

### Option B: <name>
- **Description**: <how it works>
- **Pros**: <benefits>
- **Cons**: <drawbacks>
- **Effort**: S/M/L

### Option C: <name> (if applicable)
...

## Comparison

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| <criterion 1> | ✅ / ⚠️ / ❌ | ... | ... |
| <criterion 2> | ... | ... | ... |

## Decision Rationale

<Why we chose this option. Be specific — not "it's better" but "it reduces query count from O(n) to O(1) which matters because...">

## Reversibility Assessment

- **Is this reversible?**: Yes / Partially / No
- **Cost to reverse**: Low / Medium / High
- **Point of no return**: <when does this become irreversible? e.g., "after data migration runs in prod">
- **Reversal plan**: <if we need to undo this, here's how>

## What We're Giving Up

**This section is mandatory.** Every decision has a cost. Be honest about it.

- <thing 1 we lose or can't do>
- <thing 2 we lose or can't do>
- <trade-off we're accepting>

## Consequences

- **Immediate**: <what changes now>
- **Long-term**: <what this enables or constrains in the future>
- **Documentation updates needed**: <what docs/code comments need updating>

## Follow-up Actions

- [ ] <action item with owner>
```

### Phase 3: Present for Decision

If the decision hasn't been made yet:
- Present options with clear comparison
- Highlight the reversibility assessment
- Recommend one option with reasoning
- Ask: "Which option do you want to go with?"

If recording an already-made decision:
- Fill in the rationale and mark as `🔒 Decided`

## Rules

- "What We're Giving Up" section is mandatory and non-empty
- Reversibility assessment is mandatory
- Compare alternatives when making a decision; when recording one already made, include only known alternatives/rationale and label missing context rather than inventing it
- Decision docs are never deleted — superseded ones link to their replacement
- Keep under 100 lines — brevity forces clarity
- Decision docs live in `documentation/decisions/` directory
- Reference decision docs from TRDs and story files when relevant
