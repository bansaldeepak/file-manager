---
name: prd
description: "Product Requirements Document. Tight 1-2 page PRD with problem, users, goals, scope, requirements. Runs AFTER /brief discover (if needed), BEFORE /brief trd and /brief plan. Human approval gate."
user_invocable: true
model: opus
---

# /brief prd -- Product Requirements Document

Produces a tight, actionable PRD that becomes the single source of truth for what we're building and why. Max 2 pages.

**Usage**: `/brief prd <feature or problem statement>`

**Source**: Adapted from Mehdibargach/claude-code-pm-skills PRD template.

## When Claude Should Auto-Invoke

- After `/brief discover` produces a clear opportunity and recommended path
- User describes a feature with enough clarity to define requirements
- Ask user: "Ready to write the PRD for this?"

## Human Approval Gate

**The PRD MUST be approved by the user before proceeding to `/brief trd` or `/brief plan`.** Present the PRD and explicitly ask: "Does this PRD capture the requirements correctly? Any changes before I proceed?"

## Instructions

Before drafting, follow [planning context](../references/planning-context.md). Explicitly apply relevant user decisions, rules, skills, and agent guidance; record an Applied Constraints table with their effect. Resolve known questions before execution and capture new choices immediately via [memory](../memory/SKILL.md).

### Phase 0: Branch Check

Run the branch check from `brief`'s router before writing `PRD.md` — if `git branch --show-current`
prints `main`, branch out first (`feature/<slug>` from the feature name).

### Phase 1: Gather Context

**Check project history first.** Before writing requirements, surface what the project already knows.

**Primary** — if `brief` CLI is installed (`which brief`):
```bash
brief search "<feature keywords>"
brief status
```

**Fallback** — if CLI is not installed, read files directly:
- Canonical story/item Markdown in record mode; CLI views are current. Generated tracker views may be stale.
- Legacy `documentation/tracker.yaml` only when no record-authority marker exists.
- `memory/` files — prior learnings, retro findings relevant to this feature
- Recent retro files (`documentation/stories/*/retro.md`) — what went wrong in similar work

Look for: related TODOs (maybe already identified), prior decisions (constraints that apply), retro
findings (what went wrong last time in similar work), open research. Reference anything relevant —
don't define requirements that contradict existing decisions or re-solve problems a retro already
diagnosed.

If `/brief discover` was run, reference its output. Otherwise, read relevant code, docs, and existing features to understand the problem space.

If no discovery was done and the problem seems complex, suggest running `/brief discover` first.

### PRD Structure

Every PRD must include these sections. Sections marked "conditional" can be omitted with a one-line justification.

**Required Sections (always include):**

| # | Section | Content | Satisfies (CEO Review) |
|---|---------|---------|------------------------|
| 1 | Executive Summary | 2-3 sentences, stakeholder-readable | — |
| 2 | Problem | Who has it, what they do today, what breaks | — |
| 3 | Success Metrics | Measurable outcomes with targets + how measured | §8 Observability |
| 4 | Risk Table | Likelihood × Impact × Mitigation | §3 Security, §10 Long-Term |
| 5 | Scope Modes | Must/Should/Nice + Out-of-scope with rationale | — |

**Conditional Sections (include when relevant):**

| # | Section | When to include | Satisfies |
|---|---------|-----------------|-----------|
| 6 | User Experience | When UI/UX exists | §11 Design & UX |
| 7 | Performance Requirements | When measurable perf matters | §7 Performance |
| 8 | Deployment & Rollout | When rollout has risk | §9 Deployment |
| 9 | Stakeholder Impact | When >1 team or user type | — |

**What the PRD does NOT cover (TRD owns these):** Architecture, error handling strategy, data flow details, code quality patterns, test strategy. The PRD states *what* must work; the TRD states *how*.

### Phase 2: Draft PRD

Write the PRD in this exact format. Save to `documentation/stories/<feature-name>/PRD.md`:

```markdown
# PRD: <Feature Name>

**Author**: <user/claude>
**Date**: <today>
**Status**: Draft | 🔒 Approved | Superseded
**Discovery**: <link to discovery summary if exists, or "N/A">

## Executive Summary

<2-3 sentences. A stakeholder who reads ONLY this should understand what we're building and why.>

## Problem

<2-3 sentences. What problem are we solving? For whom? What evidence do we have?>

## Users

<Who is affected? Be specific — not "all users" but "merchants who process > 100 orders/day">

| Segment | Pain Level | Current Workaround |
|---------|-----------|-------------------|
| <segment 1> | High/Med/Low | <what they do today> |

## Goals & Success Metrics

| Goal | Metric | Target | Measurement Method |
|------|--------|--------|-------------------|
| <goal 1> | <metric> | <number> | <how to measure> |

**Every metric must have a numeric target.** If you can't put a number on it, it's not a goal — it's a wish.

## What We Are Building

<Concise description of the solution. Use a Mermaid diagram for any flow.>

### Applied Constraints

| Source | Scope/status | Effect on requirements | Unresolved choice |
|--------|--------------|------------------------|-------------------|

### Requirements

| # | Requirement | Priority | Notes |
|---|------------|----------|-------|
| R1 | <requirement> | Must-have | |
| R2 | <requirement> | Must-have | |
| R3 | <requirement> | Should-have | |
| R4 | <requirement> | Nice-to-have | |

### User Flows

<Mermaid flowchart showing the primary user journey>

## What We Are NOT Building

**This section is mandatory.** Explicitly list what's out of scope and why. This prevents scope creep during implementation.

- **NOT**: <thing 1> — because <reason>
- **NOT**: <thing 2> — because <reason>

## Triggers & Edge Cases

| Trigger / Edge Case | Expected Behavior |
|--------------------|-------------------|
| <scenario> | <what should happen> |

## Dependencies

- <External service, team, data, or feature this depends on>

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <risk> | H/M/L | H/M/L | <plan> |

## Performance Requirements (conditional — when measurable perf matters)

| Metric | Target | Degradation Threshold |
|--------|--------|-----------------------|
| <metric> | <target> | <when to alert> |

## Deployment & Rollout (conditional — when rollout has risk)

- **Phasing**: <all-at-once | percentage rollout | feature flag>
- **Rollback criteria**: <what triggers rollback>
- **Migration path**: <what happens to existing users/data>

## Stakeholder Impact (conditional — when >1 team or user type)

| Stakeholder | Impact | Communication |
|-------------|--------|---------------|
| <who> | <what changes for them> | <how/when they learn> |

## Open Questions

- [ ] <Unresolved question and affected work; resolve before dependent implementation. Label future observations separately.>

## Timeline

| Milestone | Target Date | Notes |
|-----------|------------|-------|
| PRD Approved | | |
| TRD Complete | | |
| Implementation Start | | |
| MVP / First Testable | | |
| Launch | | |
```

### Phase 3: Review & Approval

Present the PRD to the user. Highlight:
- Any assumptions that haven't been validated
- Risks that could derail implementation
- Open questions that need answers

**Ask explicitly**: "Does this PRD capture the requirements correctly? Should I adjust scope, priorities, or success metrics?"

**Do NOT proceed until the user approves.** Mark status as `🔒 Approved` once confirmed.

### Phase 4: Next Step

Mark status `🔒 Approved`, then hand back to the `brief` router for the next phase — it owns the graph.

## Rules

- PRD must fit in 2 pages (roughly 100-150 lines of markdown)
- Every goal needs a numeric metric target — no vague "improve X"
- "What We Are NOT Building" section is mandatory and non-empty
- Requirements use MoSCoW priority (Must/Should/Could/Won't)
- Use Mermaid diagrams for all flows
- Reference /brief discover output if it exists — don't repeat the analysis
- PRD lives at `documentation/stories/<feature-name>/PRD.md`
- Never proceed to /brief trd or /brief plan without explicit user approval
