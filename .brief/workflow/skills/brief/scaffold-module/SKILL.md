---
name: scaffold-module
description: "Scaffold a new module in the project. Reads techstack.md for conventions, falls back to language defaults."
user_invocable: true
argument-hint: "<module-name>"
---

# /brief scaffold-module — Module Scaffold

Creates a new module directory with conventional file structure.

## Instructions

### Step 1: Detect Stack

Check for `.claude/rules/techstack.md` in the project root. If present, read it to determine:
- Language and framework (Stack section)
- Directory structure convention (Structure section)
- Path aliases (Aliases section)

If not present, detect from project files:
- `package.json` exists → Node.js/TypeScript (create: index.ts, service.ts, schemas.ts, __tests__/)
- `pyproject.toml` exists → Python (create: __init__.py, service.py, schemas.py, tests/)
- `Cargo.toml` exists → Rust (create: mod.rs, tests.rs)
- `go.mod` exists → Go (create: handler.go, service.go, handler_test.go)
- None detected → ask the user what language/framework to use

### Step 2: Determine Location

Ask the user where to create the module if not obvious from the argument:
- If techstack.md specifies a structure pattern (e.g., `app/server/modules/<name>/`), suggest that path
- Otherwise, suggest a reasonable default based on detected framework

### Step 3: Create Files

For each file in the module template:
1. Create the directory: `mkdir -p <module-path>`
2. Create each file with minimal boilerplate appropriate to the framework
3. If the framework uses barrel exports (index.ts/index.py), create one that re-exports from the other files

### Step 4: Report

List created files and suggest next steps:
- "Module created at <path>. Add routes/endpoints and implement service logic."
- If tests directory created: "Test file ready at <test-path>."

## Rules

- Never overwrite existing files
- Always create a test file alongside the module
- Follow the project's naming conventions from techstack.md or coding-style.md
- Ask before creating if the target directory already exists
