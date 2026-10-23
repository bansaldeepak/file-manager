---
name: memory
description: "Capture and recall scoped project decisions and user preferences; define canonical storage, provenance, promotion, and reconciliation checkpoints."
---

# Project Memory

The repository is authoritative: MEMORY.md is a short index; durable facts live in
documentation/memory/, decisions in documentation/decisions/, and feature context beside stories
or architecture docs. Respect an explicitly configured legacy repo layout. Never store project
knowledge in provider-global memory or expand a choice beyond its stated scope.

## Capture When the User Decides

The active agent records explicit design, naming, functional, or workflow choices immediately,
including during unfinished planning. Do not wait for retro. Recording an already-made choice
needs no repeat approval; adopting an inferred preference or promoting to broader scope does.

For each distinct fact record:
- Choice and source: user statement/date and repo artifact reference when available.
- Stated scope: feature, module/path, project, or explicitly shared; if unclear, ask before wider use.
- Status: explicitly decided, observed/proposed, superseded, or retired.
- Rationale and rejected alternatives only when supplied or actually established; don't invent them.
- How to apply and, when relevant, how to verify; link replacement/related decisions.

Record a narrowly applicable decision now even if its possible broader relevance is unresolved.
An observation of existing code is not proof of a user preference.

## Read and Write Contract

With the CLI, use `brief memory list --all` for inventory, `brief memory show <slug>` for details,
and `brief search "<area>"` across decisions/retros/context. Read relevant entries, not the entire
store every task. The index is not the full inventory.

Use CLI mutations where available:
```bash
brief memory create "<title>" --memtype=feedback --importance=4 --valid-until=permanent --body="<fact and provenance>"
brief memory update <slug> updated=<YYYY-MM-DD> --body="<revised fact and provenance>"
brief memory retire <slug>
```

CLI supports feedback, project, reference, and user memory types; slug filenames are returned by
create. For multiline bodies prefer stdin with `--body=-`. Verify the written content.
If the active agent/curator lacks CLI access, hand mutations to the caller; if no CLI is available,
read the same canonical files and restore CLI access before record-mode creation/status changes.
For legacy-only projects, direct fallback edits must reconcile the legacy index/tracker without dropping entries.

Follow [record/log storage](../references/records-and-installation.md); preserve reserved `_brief` metadata and use immutable new log entries.

Current CLI files use `metadata.type`; accept historical top-level `type` when reading. Do not
bulk-convert old records just to match a template. New direct-write fallback:
```yaml
---
name: descriptive-name
description: Concise retrieval description
metadata:
  type: feedback
created: YYYY-MM-DD
updated: YYYY-MM-DD
valid_until: permanent
importance: 4
---
```
Source/scope/decision-status/application belong in the body so existing CLI readers remain compatible.
Set validity deliberately: user/feedback permanent, active project context 30–90 days, references
about six months. Importance 4–5 requires revalidation before retirement; expiration alone does
not revoke an explicit user preference.

## Recall and Apply

Use [planning context](../references/planning-context.md) before PRD/TRD/tasks and during execution
and review. Make relevant decisions' effects explicit. Current user instructions apply within their
scope; reconcile older conflicting records. Unresolved contradictions require clarification.
Code violating a preference does not invalidate that preference. Do not re-ask settled choices.

## Destinations and Promotion

| Knowledge | Destination |
|-----------|-------------|
| Durable user choice or correction | documentation/memory/ |
| Architectural trade-offs | documentation/decisions/; link from TRD and tasks |
| Feature implementation gotcha | feature context.md |
| Reusable path convention | Project rule, after applicable authorization |
| Repeatable procedure or agent behavior | Skill or agent source, after applicable authorization |
| Deferred work | Tracked TODO with owner/trigger |

Retro/curation must apply and verify authorized rule/skill/agent improvements, not merely suggest
them. Reuse explicit approval within scope; ask before wider promotion. Preserve source rationale
and supersession links. Before retiring a duplicate/promoted fact, verify the destination exists
and is retrievable. Retire rather than delete history. Never promote to provider-global configuration
merely because an observation recurred.

## Reconciliation Checkpoints

Immediate capture is primary. Reconcile omissions after planning, implementation, and at retro;
capture new post-publication outcomes when observed. If nothing is notable, state that.
Pass captured conversation choices and their sources to a curator; it cannot recover unseen turns.

Keep MEMORY.md concise, with pointers to active work and durable knowledge. Flush inactive feature
details to its context.md while retaining retrievable provenance. Inventory entries before/after
curation and account for every moved/retired pointer; index length is not a reason to lose knowledge.
Use the story's commit mode for memory/bookkeeping changes; never infer push authority.
