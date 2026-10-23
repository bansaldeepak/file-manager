---
name: discover
description: "Structured problem discovery and validation. Runs BEFORE /brief prd to ensure we're solving the right problem. Brainstorm → Assumptions → Experiments → Discovery Plan."
user_invocable: true
model: opus
---

# /brief discover -- Problem Discovery Skill

Structured problem validation before writing requirements. Ensures we understand the problem space deeply before committing to a solution direction.

**Usage**: `/brief discover <problem area, feature idea, or user pain point>`

**Source**: Adapted from phuryn/pm-skills discovery workflow (Teresa Torres' Opportunity Solution Tree).

## When Claude Should Auto-Invoke

- User describes a vague feature idea without clear problem definition
- Scope is ambiguous and multiple interpretations exist
- The request could affect multiple user segments differently
- Ask user: "This seems like it needs discovery first. Want me to run `/brief discover`?"

## Instructions

You are entering discovery mode. Do NOT write code, stories, PRDs, or tasks. Your job is to deeply understand the problem space and produce a discovery plan.

### Phase 1: Context Gathering

**Check project history first.** Before exploring the codebase, surface what the project already knows
about this problem area.

**Primary** — if `brief` CLI is installed (`which brief`):
```bash
brief search "<problem keywords>"
brief status
```

**Fallback** — if CLI is not installed, read files directly:
- Canonical story/item Markdown in record mode; CLI views are current. Generated tracker views may be stale.
- Legacy `documentation/tracker.yaml` only when no record-authority marker exists.
- `memory/` files — prior learnings, gotchas, retro findings
- Recent retro files (`documentation/stories/*/retro.md`) — patterns from similar past work

Look for: prior retro findings, open TODOs, existing decisions, related research. These are inputs
to discovery — don't re-discover what's already known.

Then read relevant code, docs, analytics, and user-facing flows to understand the current state.

**Output**: A "Current Reality" section with:
- How things work today (Mermaid diagram)
- Known pain points or friction (include any from tracker/retros)
- Existing workarounds users employ

### Phase 1b: Mode Detection

Auto-detect the work type from the user's description:

| Mode | Signal | Adjusts |
|------|--------|---------|
| `greenfield` | "new", "build", "add" — no prior art exists | Focus on scope boundaries, MVP definition |
| `bug` | "broken", "fails", "error" — something that worked now doesn't | Focus on reproduction, root cause, blast radius |
| `optimization` | "slow", "expensive", "timeout" — working but poorly | Focus on measurement, targets, constraints |
| `refactor` | "messy", "hard to change", "coupled" — working but structurally wrong | Focus on what's wrong structurally, what "done" looks like |

State the detected mode explicitly: "This sounds like a **greenfield** problem — is that right?"
Adjust follow-up emphasis based on mode, but always ask all 5 forcing questions.

### Phase 1c: Forcing Questions

Ask ONE at a time. Wait for the answer before asking the next. Do not batch.

1. **"Who specifically is affected? Name the user type and their workflow."**
   - Reject: "users", "people", "everyone" — push for a specific role/persona

2. **"What do they do today without this? What breaks or is painful?"**
   - Reject: "it's hard", "not great" — push for the concrete current workaround

3. **"How will you know this worked? What measurable outcome changes?"**
   - Reject: "it'll be better", "faster" — push for a number, metric, or observable behavior

4. **"What's the smallest version that delivers value? What can wait?"**
   - Reject: "all of it is needed" — push: what would you ship if you had one day?

5. **"What have you already tried or ruled out? Why didn't it work?"**
   - Accept: "nothing yet" — that's a valid answer. Don't push.

#### Push Rule

If any answer contains vague language without specifics ("users", "better", "improve", "faster", "easier"), push ONCE:

> "Can you be more specific? Which users, what specifically is better, how do you measure improvement?"

Push only once per question. If the second answer is still vague, accept it and move on — note the vagueness as a risk in the discovery output.

### Phase 2: Brainstorm (Multi-Perspective)

Generate ideas from three lenses:
- **User lens**: What does the user actually need? What job are they trying to do?
- **Technical lens**: What's possible? What constraints exist? What's surprisingly easy or hard?
- **Business lens**: What moves the needle? What's the cost of inaction?

For each perspective, generate 3-5 opportunity statements:
> "Users who [context] need a way to [job-to-be-done] so they can [outcome]"

### Phase 3: Identify Assumptions

For each top opportunity, list assumptions across four categories:

| Category | Question |
|----------|----------|
| **Value** | Will users want this? Will it solve their problem? |
| **Usability** | Can users figure out how to use it? |
| **Feasibility** | Can we build it with current tech/resources? |
| **Viability** | Does it work for the business? Compliance? Cost? |

**Prioritize assumptions** using Impact × Risk:
- **High Impact, High Risk** → Must test before building
- **High Impact, Low Risk** → Monitor but proceed
- **Low Impact** → Ignore for now

### Phase 3b: Pre-Mortem (Stress-Test the Top Opportunity)

Before investing in experiments, stress-test the leading direction:

> "Imagine we built this and shipped it. Six months later, it's considered a failure. What went wrong?"

Evaluate from 4 angles:
1. **Technical** — What could be harder than it looks? What breaks under load, edge cases, or real data?
2. **Product** — What if users don't adopt it? What if it solves the wrong problem?
3. **Process** — What if we underestimate scope? What dependencies could block us?
4. **External** — What market/regulatory/competitive changes could make this irrelevant?

For each risk, categorize:
- **Must-mitigate** — address in PRD scope or constraints (feeds into Risk Table)
- **Acceptable** — acknowledged, won't derail the initiative

Surface the must-mitigate risks in the Discovery Plan output. These become constraints that the PRD must address.

### Phase 4: Design Experiments (for High-Risk Assumptions)

For each high-risk assumption, propose a lightweight experiment:

```markdown
### Assumption: <statement>
- **Risk level**: High
- **Experiment**: <what to do to validate>
- **Signal**: <what result would confirm/deny>
- **Effort**: Hours / Days / Weeks
- **Can we test before building?**: Yes/No
```

Prefer experiments that don't require code: user interviews, data analysis, prototypes, competitive analysis, manual processes.

### Phase 5: Discovery Plan

Compile into a structured output:

```markdown
## Discovery Summary

### Problem Space
<2-3 sentences capturing the core problem area>

### Top Opportunities (ranked by Opportunity Score: Importance × (1 - Satisfaction))
1. **O1: <name>** — <one-line summary> [Score: H/M/L]
2. **O2: <name>** — <one-line summary> [Score: H/M/L]

### Critical Assumptions to Validate
1. **A1**: <assumption> → Experiment: <method> → Timeline: <effort>
2. **A2**: <assumption> → Experiment: <method> → Timeline: <effort>

### What We Already Know (Low-Risk Assumptions)
- <assumption we're confident about and why>

### Recommended Path
<Which opportunity to pursue, which assumptions to validate first>

### Open Questions
<Things we can't answer without research or user input>

### Next Step
- If assumptions need validation: "Run experiments, then `/brief prd <focused-scope>`"
- If problem is clear enough: "Ready for `/brief prd <specific-feature>`"
- If trivial: "This is small enough to skip to `/brief plan`"
```

**Wait for user input before proceeding to /brief prd.**

### Phase 6: Persist

Write the discovery summary to `documentation/stories/<feature>/DISCOVERY.md`. The feature folder
should already exist (created at branch check). If it doesn't, create it with `mkdirSync`.

The DISCOVERY.md must contain all findings from the discovery conversation:
- Current Reality (with Mermaid diagram)
- Forcing Questions — Answers table
- Brainstorm (all three lenses)
- Assumptions & Risk table
- Pre-Mortem findings
- Experiments to Validate
- Top Opportunities (ranked)
- Design Decisions (from discovery)
- Recommended Path
- Open Questions

Conversation output alone is not sufficient — it's lost when the session ends. The file is the
deliverable, not the conversation.

## Rules

- Never jump to solutions — stay in problem space
- At least 3 distinct opportunities before converging
- At least 2 experiments per high-risk assumption
- Use Mermaid diagrams for any flow or relationship
- Challenge the premise: "Do we even need to solve this?" is valid
- If the problem is trivial (< 30 min), say so and redirect to `/brief plan`
- Keep output under 400 lines
- Invoke the `researcher` agent for deep codebase/data exploration if needed
