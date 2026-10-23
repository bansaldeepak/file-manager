#!/usr/bin/env python3
"""Generate a Codex custom-agent TOML from a shared agent definition.

Usage: gen-codex-agent.py <agents/name.md>   # TOML on stdout

The source of truth is `~/.agents/agents/<name>.md` — Claude Code reads that file
directly via symlink, Codex needs this translation. The two formats are NOT
isomorphic; what does not map is reported on stderr so build.sh can surface it
rather than silently dropping it.

Mapping
    name                -> name
    description         -> description
    body                -> developer_instructions
    model               -> model + model_reasoning_effort
    tools/disallowed    -> sandbox_mode  (approximate — see below)
    maxTurns, memory    -> dropped (no Codex equivalent)

Codex has no per-tool allowlist. The closest lever is the sandbox: an agent that
cannot Write or Edit becomes read-only, anything else gets workspace-write. That
is coarser than the Claude side — a read-only Codex agent can still call any
tool, it just cannot persist changes.
"""

import re
import sys
from pathlib import Path

# Claude model alias -> (Codex model, reasoning effort)
MODEL_MAP = {
    "haiku": ("gpt-5.6-terra", "low"),
    "sonnet": ("gpt-5.6", "medium"),
    "opus": ("gpt-5.6", "high"),
}

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
DROPPED_KEYS = {"maxTurns", "memory", "disallowedTools", "tools", "model", "name", "description"}


def parse(text):
    """Split a SKILL/agent markdown file into (frontmatter dict, body)."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        raise SystemExit("no frontmatter found")
    raw, body = m.group(1), m.group(2).strip()

    meta, key = {}, None
    for line in raw.split("\n"):
        if not line.strip():
            continue
        if re.match(r"^\s+-\s", line):  # list item under the previous key
            meta.setdefault(key, []).append(line.strip()[2:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            meta[key] = val if val else []
    return meta, body


def toml_multiline(value):
    """Escape a string for a TOML triple-quoted literal."""
    return value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def main():
    if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != "--label"):
        raise SystemExit(__doc__)
    src = Path(sys.argv[1])
    meta, body = parse(src.read_text())

    name = meta.get("name") or src.stem
    description = meta.get("description", "")
    tools = meta.get("tools") or []
    tools = tools if isinstance(tools, list) else [tools]

    model_alias = meta.get("model", "")
    model, effort = MODEL_MAP.get(model_alias, (None, None))
    if model_alias and model is None:
        print(f"  ! {name}: unknown model '{model_alias}' — inheriting session default",
              file=sys.stderr)

    sandbox = "workspace-write" if (WRITE_TOOLS & set(tools)) else "read-only"

    dropped = [k for k in meta if k in DROPPED_KEYS and k not in ("name", "description", "model")]
    if dropped:
        print(f"  ! {name}: no Codex equivalent for {', '.join(sorted(dropped))} "
              f"— approximated as sandbox_mode = \"{sandbox}\"", file=sys.stderr)

    out = [
        f"# Generated from {sys.argv[3] if len(sys.argv) == 4 else src.resolve()} — do not edit.",
        "# Edit the source and re-run this checkout’s build.sh instead.",
        "",
        f'name = "{name}"',
        f'description = "{description}"',
    ]
    if model:
        out.append(f'model = "{model}"')
        out.append(f'model_reasoning_effort = "{effort}"')
    out.append(f'sandbox_mode = "{sandbox}"')
    out.append("")
    out.append(f'developer_instructions = """\n{toml_multiline(body)}\n"""')
    print("\n".join(out))


if __name__ == "__main__":
    main()
