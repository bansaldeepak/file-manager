---
name: brief-init
description: "Reads project code, infers conventions, fills rule skeletons with real content using marker-based merge. Run after `brief init` to populate rules with project-specific conventions."
user_invocable: true
model: sonnet
---

# /brief init — Fill Rule Skeletons with Project Conventions

## When to Use

After running `brief init` (CLI) which creates rule files with empty markers. This skill reads
your code and fills those markers with real conventions.

## Instructions

### Step 1: Verify Brief is Installed

Read [installation and records](../references/records-and-installation.md), then run `brief doctor`.
Local installs use `.brief/workflow/manifest.json`; global-selected projects record scope in
`.brief/install.json`. Old `.brief/brief-manifest.json` is supported only for legacy installs.
Do not assume a missing legacy manifest means a portable install is absent.

### Step 2: Understand What's Present

Inspect project rule directories and package configuration to identify installed rule skeletons,
providers and the actual tech stack. Portable provenance records package hashes/ownership, not
machine-specific stack detection. Respect the selected scope and pinned package; filling project
rule skeletons is separate from an explicit package update.

### Step 3: Read Project Code

Based on detected stack, read representative files to infer conventions:
- `package.json` — deps, scripts, type field
- `tsconfig.json` — compiler options, paths, strictness
- 3-5 source files from `src/` or the main source directory — naming, import style, patterns
- 1-2 test files — test runner, assertion patterns
- `.eslintrc*`, `eslint.config.*`, or `biome.json` — linting rules already defined

### Step 4: Infer Conventions

From the code, determine:
- **Naming**: camelCase/snake_case for functions, PascalCase for types, file naming pattern
- **Imports**: ESM/CJS, path aliases, barrel exports
- **Testing**: runner (vitest/jest/mocha), pattern (describe/it vs test()), mocking approach
- **Framework idioms**: specific to detected framework (Hono c.json(), Prisma patterns, React hooks)
- **Error handling**: typed errors, Result patterns, try/catch conventions
- **Architecture**: layer patterns (handlers → services → providers), module boundaries

Only include conventions you can confidently infer from the code. Omit anything uncertain.

### Step 5: Fill Each Rule File

For each applicable project rule skeleton found:

1. Read the file (check all agent locations: `.claude/rules/`, `AGENTS.md`, `.agents/rules/`)
2. Look for `<!-- brief:auto section="..." -->` ... `<!-- /brief:auto -->` markers
3. Generate concise convention content for each section found
4. Replace only the content between markers — never touch content outside markers
5. Write back

**Per-agent format awareness:**
- `.claude/rules/*.md` — keep frontmatter intact, fill conventions after it
- `AGENTS.md` — keep concise (<2KB for the brief section), conventions only
- `.agents/rules/*.md` — fill directly (plain markdown)

**Content style:**
- Use present tense imperatives: "Use ESM imports", not "The project uses ESM imports"
- Bullet points, not paragraphs
- Concrete: include actual patterns from the codebase (function names, file paths)
- Concise: 5-15 bullet points per section

### Step 6: Report

Print what was filled/updated. Example:
```
Filled rules:
  .claude/rules/coding-style.md — 8 conventions inferred
  .claude/rules/backend-standards.md — 5 framework patterns
  AGENTS.md — conventions section updated (1.2KB)
  .agents/rules/coding-style.md — mirrored from Claude rules
```

## Rules

- Never modify content outside `<!-- brief:auto -->` ... `<!-- /brief:auto -->` markers
- If markers are corrupted (nested, unclosed): skip that file, warn the user
- Keep generated content concise — bullet points, not essays
- If you can't infer something confidently, omit it rather than guessing
- Re-running must be safe: only marker content changes, everything else preserved
- Do not add new marker sections — only fill existing ones placed by `brief init`
