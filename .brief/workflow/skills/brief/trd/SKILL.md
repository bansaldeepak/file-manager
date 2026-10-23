---
name: trd
description: "Technical Requirements Document. Architecture design, system design, data model changes, API contracts, technical constraints. Runs AFTER /brief prd approval, BEFORE /brief plan. Human approval gate when architecture changes are involved."
user_invocable: true
model: opus
---

# /brief trd -- Technical Requirements Document

Translates approved PRD requirements into technical architecture and design decisions. Ensures architecture is reviewed before implementation begins.

**Usage**: `/brief trd <feature name>` (references the approved PRD)

## When Claude Should Auto-Invoke

- After PRD is approved and the feature involves:
  - New database tables/columns or schema changes
  - New API endpoints or changes to existing contracts
  - New services, modules, or significant refactoring
  - Third-party integrations
  - Performance-sensitive features
  - Security-sensitive features
- For simple features (UI-only, config changes), skip TRD and go to `/brief plan`
- Prepare the required TRD within authorized scope; reuse approval to begin this phase. Architecture approval remains required before implementation unless already explicitly authorized.

## Human Approval Gate

**The TRD MUST be approved by the user before proceeding to `/brief plan` when architecture changes are involved.** Present the TRD and explicitly ask: "Does this technical approach look right? Any concerns before I plan the implementation?"

## Instructions

Before drafting, follow [planning context](../references/planning-context.md). Explicitly apply relevant user decisions, rules, skills, and agent guidance; record an Applied Constraints table with their effect. Resolve known questions before execution and capture new choices immediately via [memory](../memory/SKILL.md).

### Phase 0: Branch Check

Run the branch check from `brief`'s router before writing `TRD.md`. Normally you're still on the
feature branch `prd` created — if `git branch --show-current` prints `main` instead, branch out now.

### Phase 1: Read the PRD

Read `documentation/stories/<feature-name>/PRD.md`. If it doesn't exist or isn't approved, stop and redirect to `/brief prd`.

### Phase 2: Assess Current Architecture

Use the `researcher` agent to:
- Map current system architecture relevant to this feature
- Identify existing patterns, services, and data models
- Find integration points and boundaries
- Check for existing technical debt that affects this work

**Output**: "Current Architecture" section with Mermaid diagram.

### TRD Structure

Every TRD must include these sections. Aligned with what `/gstack plan-eng-review` checks.

**Required Sections (always include):**

| # | Section | Satisfies (Eng Review) |
|---|---------|------------------------|
| 1 | Architecture Decisions | §1 Architecture |
| 2 | Error Handling & Failure Modes | §1 Architecture, §2 Error/Rescue |
| 3 | Testing Strategy | §3 Test Review |
| 4 | Rollback Plan | §9 Deployment |
| 5 | Dependencies | §1 Architecture |
| 6 | Verification | §3 Test Review |

**Conditional Sections (include when relevant):**

| # | Section | When | Satisfies |
|---|---------|------|-----------|
| 7 | Security & Threat Model | Auth/data/APIs involved | §3 Security |
| 8 | Observability Plan | System has runtime behavior | §8 Observability |
| 9 | Performance | Data/traffic/latency matters | §4 Performance |
| 10 | Long-Term Trajectory | Architecture is hard to undo | §10 Long-Term |

**Required Outputs (eng review expects these):**
- Error/Rescue Registry — maps every known error → handler → user message
- Failure Modes — each failure with trigger, impact, mitigation
- Coverage Diagram — visual map of test coverage
- Implementation Task List — ordered tasks with dependencies

### Phase 3: Draft TRD

Write the TRD in this format. Save to `documentation/stories/<feature-name>/TRD.md`:

```markdown
# TRD: <Feature Name>

**Author**: <user/claude>
**Date**: <today>
**Status**: Draft | 🔒 Approved | Superseded
**PRD**: [PRD.md](./PRD.md)

## Overview

<1-2 sentences: What technical changes are needed to fulfill the PRD requirements?>

## Current Architecture

<Mermaid diagram showing relevant parts of the current system>

## Applied Constraints

| Source decision/rule | Scope/status | Effect on design/schema/naming | Verification or unresolved choice |
|----------------------|--------------|--------------------------------|-----------------------------------|

## Proposed Architecture

<Mermaid diagram showing the target state>

### What Changes

| Component | Change Type | Description |
|-----------|------------|-------------|
| <component> | New / Modified / Removed | <what changes> |

## Data Model

### Schema Changes

<Mermaid ER diagram if database changes are involved>

```sql
-- Migration pseudocode (not final — final migration created during implementation)
ALTER TABLE ...
CREATE TABLE ...
```

### Data Migration

- **Backwards compatible?**: Yes/No
- **Migration strategy**: <online migration, backfill script, etc.>
- **Rollback plan**: <how to undo if something goes wrong>

## API Design

### New/Modified Endpoints

| Method | Path | Request | Response | Auth | Notes |
|--------|------|---------|----------|------|-------|
| POST | /api/... | `{ body }` | `{ data: T }` | Required | |

### API Contracts

<Zod schema definitions or TypeScript interfaces for request/response shapes>

## System Design

### Component Interaction

<Mermaid sequence diagram showing how components interact for key flows>

### Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| <decision> | A, B, C | B | <why B wins> |

**Record every non-obvious technical decision here.** These become the project's technical memory.

Keep the decision table and expanded design consistent with the actual approved choice. If they conflict, check decision provenance and seek clarity when unresolved; neither a table row nor existing code can silently override user intent.

### Design Patterns

<Which existing patterns to follow, or new patterns being introduced>
- Pattern: <name> — Used for: <what> — Reference: <existing example in codebase>

## Error Handling & Failure Modes

### Exception Table

| Error | Handler | User-Visible Result |
|-------|---------|---------------------|
| <what can go wrong> | <how it's caught> | <what user sees> |

### Failure Modes

| Failure | Trigger | Impact | Mitigation |
|---------|---------|--------|------------|
| <mode> | <condition> | <blast radius> | <how prevented/recovered> |

## Performance Considerations

- **Expected load**: <requests/sec, data volume, concurrent users>
- **Bottlenecks**: <identified hot paths>
- **Caching strategy**: <if applicable>
- **Query complexity**: <any N+1 risks, heavy joins>

## Security Considerations

- **Auth/AuthZ changes**: <what changes to access control>
- **Data sensitivity**: <PII, financial data, etc.>
- **Input validation**: <attack surface changes>
- **OWASP top 10 relevance**: <which apply>

## Observability Plan (conditional — when system has runtime behavior)

- **Logging**: <what state transitions to log, correlation ID strategy>
- **Metrics**: <counters/gauges/histograms to emit>
- **Alerts**: <what triggers a page, thresholds>
- **Runbooks**: <where to find them, or draft inline>

## Dependencies

| Dependency | Type | Risk | Mitigation |
|-----------|------|------|------------|
| <dep> | Internal/External/Package | H/M/L | <plan> |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | <services, utils> | Mock dependencies |
| Integration | <API endpoints, DB queries> | Real DB, test fixtures |
| E2E | <user flows> | If applicable |

### Coverage Diagram

<ASCII or Mermaid diagram showing which components/paths are covered by tests>

## Verification (beyond tests)

- **Integration checks**: <how to verify with real systems>
- **Smoke test scenarios**: <post-deploy quick checks>
- **Manual verification**: <what a human checks, if applicable>

## Rollback Plan

| Story/Task | Revert Strategy | Data Implications | User Impact |
|------------|----------------|-------------------|-------------|
| <scope> | <git revert / flag off / migration down> | <state created?> | <during rollback> |

## Long-Term Trajectory (conditional — when architecture is hard to undo)

- **Trade-offs**: <explicit approved choices and rationale; confirmed new review defects still require correction>
- **Reversibility**: <1-5 scale, where 5 = easily reversible>
- **Path dependency**: <what future options this closes/opens>

## Open Technical Questions

- [ ] <Unresolved question, affected tasks, and dependent-work block; resolve before execution. Label future observations separately.>

## Implementation Order (High-Level)

<Suggested order of implementation — this feeds into `/brief plan` task breakdown>

1. <First: data model / schema changes>
2. <Second: service layer>
3. <Third: API endpoints>
4. <Fourth: frontend>
5. <Fifth: tests and integration>
```

### Phase 4: Review & Approval

Before presenting to the user, **verify consistency**:
- Run: `grep -n "Chosen:" TRD.md` and verify each "Chosen:" line in the expanded sections matches its corresponding table row exactly
- Resolve contradictions against approved decisions/user instructions; ask if unresolved before changing the design

Present the TRD to the user. Highlight:
- Architecture decisions that have long-term implications
- Trade-offs made and alternatives considered
- Risks and their mitigations
- Any open technical questions that need resolution

**Ask explicitly**: "Does this technical approach look right? Any concerns about the architecture, data model, or design decisions?"

**Do NOT proceed to `/brief plan` until the user approves architecture changes.**

For minor technical details (naming, file structure), user can defer to Claude's judgment.

### Phase 5: Update Documentation

After TRD approval:
- If new patterns are introduced, update relevant documentation
- If architecture docs exist, update them to reflect planned changes
- Reference the TRD from the PRD (add link)

### Phase 6: Next Step

Mark status `🔒 Approved`, then hand back to the `brief` router for the next phase — it owns the graph.

## Rules

- TRD must reference an approved PRD — redirect to `/brief prd` if missing
- Every design decision must list alternatives considered
- Use Mermaid diagrams for architecture, data model, and sequence flows
- Schema changes must include rollback plan
- Security and performance sections are mandatory (even if "N/A — no changes")
- Design decisions recorded here become the project's technical memory
- TRD lives at `documentation/stories/<feature-name>/TRD.md`
- Never proceed to /brief plan for architecture changes without user approval
- Keep the TRD focused — implementation details belong in task descriptions, not here
