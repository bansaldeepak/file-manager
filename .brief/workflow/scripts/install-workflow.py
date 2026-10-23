#!/usr/bin/env python3
"""Install only brief-owned registrations and a managed block, preserving other host configuration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
LINK_ROOT = ROOT
OPEN = "<!-- brief:workflow -->"
CLOSE = "<!-- /brief:workflow -->"
AGENTS = ("qa", "reviewer", "researcher", "self-improving")
RULES = ("brief", "brief-lifecycle", "git-workflow", "db-safety")
CONFIGS = (".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(prefix=".brief-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def block_bounds(text):
    if OPEN not in text and CLOSE not in text:
        return None
    if text.count(OPEN) != 1 or text.count(CLOSE) != 1 or text.index(CLOSE) < text.index(OPEN):
        raise ValueError("malformed or duplicate brief workflow markers")
    return text.index(OPEN), text.index(CLOSE) + len(CLOSE)


def integrate_config(text, block):
    bounds = block_bounds(text)
    if bounds:
        start, end = bounds
        return text[:start] + block + text[end:]
    # Ownership applies only to the managed block; preserve all surrounding bytes as text.
    return text + ("\n" if text.endswith("\n") else "\n\n") + block + "\n"


def targets():
    result = {}
    for host in (".agents", ".claude", ".codex"):
        result[f"{host}/skills/brief"] = ("link", str(LINK_ROOT / "skills/brief"))
        for rule in RULES:
            result[f"{host}/rules/{rule}.md"] = ("link", str(LINK_ROOT / f"rules/{rule}.md"))
    for name in AGENTS:
        for host in (".agents", ".claude"):
            result[f"{host}/agents/{name}.md"] = ("link", str(LINK_ROOT / f"agents/{name}.md"))
        generated = subprocess.run([sys.executable, str(ROOT / "scripts/gen-codex-agent.py"),
                                    str(ROOT / f"agents/{name}.md"), "--label", str(LINK_ROOT / f"agents/{name}.md")],
                                   capture_output=True, text=True)
        if generated.stderr:
            print(generated.stderr, end="", file=sys.stderr)
        generated.check_returncode()
        result[f".codex/agents/{name}.toml"] = ("file", generated.stdout)
    adapter = (ROOT / "templates/WORKFLOW-ADAPTER.md").read_text().replace("@BRIEF_SOURCE@", str(LINK_ROOT))
    for path in CONFIGS:
        result[path] = ("block", OPEN + "\n" + adapter.rstrip() + "\n" + CLOSE)
    return result


def safe_path(home, relative):
    path = home / relative
    for ancestor in (path.parent, *path.parent.parents):
        if os.path.lexists(ancestor) and not ancestor.is_dir():
            raise ValueError(f"destination ancestor is not a directory: {ancestor}")
    actual = path.parent.resolve() / path.name
    if not actual.is_relative_to(home.resolve()):
        raise ValueError(f"destination parent escapes installation root: {relative}")
    return path, actual


def read_manifest(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    valid = (isinstance(data, dict) and data.get("version") == 1
             and isinstance(data.get("source"), str) and Path(data["source"]).is_absolute()
             and isinstance(data.get("entries"), dict) and bool(data["entries"]))
    if valid:
        for name, entry in data["entries"].items():
            if (not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts
                    or not isinstance(entry, dict)):
                valid = False
                break
            kind = entry.get("kind")
            value = entry.get("target" if kind == "link" else "sha256")
            if (kind not in ("link", "file", "block") or not isinstance(value, str)
                    or (kind == "link" and not Path(value).is_absolute())
                    or (kind != "link" and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)))):
                valid = False
                break
    if not valid:
        raise ValueError("unrecognized brief workflow manifest; preserve or relocate it before installing")
    return data


def make_plan(home, previous, adopt):
    plan, conflicts, seen = [], [], {}
    for relative, (kind, payload) in targets().items():
        path, actual = safe_path(home, relative)
        key = str(actual)
        if key in seen:
            if seen[key] != (kind, payload):
                raise ValueError(f"conflicting aliased destinations: {relative}")
            continue
        seen[key] = (kind, payload)
        old = previous.get(relative, {})
        exists = os.path.lexists(path)
        expected = {"kind": kind, "target": payload} if kind == "link" else {"kind": kind, "sha256": digest(payload)}
        content, owned, matches = payload, False, False
        if kind == "link":
            if not (ROOT / Path(payload).relative_to(LINK_ROOT)).exists():
                raise ValueError(f"missing source: {payload}")
            matches = path.resolve() == Path(payload).resolve() and exists
            owned = path.is_symlink() and old.get("kind") == "link" and os.readlink(path) == old.get("target")
        elif exists:
            if path.is_symlink() or not path.is_file():
                conflicts.append(f"{relative}: expected a regular generated/config file")
                continue
            current = path.read_text()
            if kind == "block":
                bounds = block_bounds(current)
                current_block = current[slice(*bounds)] if bounds else None
                matches = current_block == payload
                owned = bounds is None or (old.get("kind") == "block" and digest(current_block) == old.get("sha256"))
                content = integrate_config(current, payload)
            else:
                matches = current == payload
                owned = old.get("kind") == "file" and digest(current) == old.get("sha256")
        elif kind == "block":
            content = payload + "\n"
        if exists and not matches:
            if path.is_dir() and not path.is_symlink():
                conflicts.append(f"{relative}: refusing to replace a directory")
                continue
            if not owned and not adopt:
                conflicts.append(f"{relative}: unowned or modified; inspect dry-run then explicitly adopt with backup")
                continue
        if actual.is_relative_to(ROOT) and not matches:
            conflicts.append(f"{relative}: destination would overwrite source checkout")
            continue
        plan.append({"path": path, "relative": relative, "kind": kind, "payload": content,
                     "expected": expected, "change": not matches})
    return plan, conflicts


def backup(path, target):
    if not os.path.lexists(path):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        target.symlink_to(os.readlink(path))
    else:
        target.write_bytes(path.read_bytes())
        os.chmod(target, stat.S_IMODE(path.stat().st_mode))


def install(home, plan, manifest_path):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root, _ = safe_path(home, f".agents/brief-backups/{timestamp}")
    # Preflight destinations is complete before any write. Each replacement is atomic; backups
    # remain on failure and a repeat invocation can recognize already-installed exact content.
    for item in plan:
        if not item["change"]:
            continue
        path = item["path"]
        backup(path, backup_root / item["relative"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if item["kind"] == "link":
            fd, temporary = tempfile.mkstemp(prefix=".brief-link-", dir=path.parent)
            os.close(fd)
            os.unlink(temporary)
            try:
                os.symlink(item["payload"], temporary)
                os.replace(temporary, path)
            finally:
                if os.path.lexists(temporary):
                    os.unlink(temporary)
        else:
            atomic_write(path, item["payload"])
    data = {"version": 1, "source": str(LINK_ROOT), "entries": {i["relative"]: i["expected"] for i in plan}}
    serialized = json.dumps(data, indent=2) + "\n"
    if not manifest_path.exists() or manifest_path.read_text() != serialized:
        backup(manifest_path, backup_root / ".agents/brief-workflow.json")
        atomic_write(manifest_path, serialized)
    if backup_root.exists():
        print(f"Backups: {backup_root}")


def main():
    global ROOT, LINK_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home-dir", type=Path, default=Path.home(), help="Installation root; use a temporary directory for tests")
    parser.add_argument("--source-dir", type=Path, default=ROOT, help="Workflow checkout or packaged source")
    parser.add_argument("--link-source", type=Path, help="Prospective package location for preflight")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--plan-json", action="store_true", help="Read-only transaction plan for the scoped package installer")
    parser.add_argument("--adopt-existing", action="store_true", help="Explicitly replace named existing files/links with backups; never directories")
    args = parser.parse_args()
    ROOT = args.source_dir.expanduser().resolve()
    LINK_ROOT = (args.link_source or ROOT).expanduser().absolute()
    if args.link_source and not (args.dry_run or args.plan_json):
        raise ValueError("--link-source is only supported for read-only preflight")
    home = args.home_dir.expanduser().absolute()
    manifest, actual_manifest = safe_path(home, ".agents/brief-workflow.json")
    safe_path(home, ".agents/brief-backups/preflight")
    if actual_manifest.is_relative_to(ROOT):
        raise ValueError("manifest would overwrite source checkout")
    if manifest.is_symlink():
        raise ValueError("refusing symlink manifest")
    prior_manifest = read_manifest(manifest)
    previous = prior_manifest.get("entries", {})
    plan, conflicts = make_plan(home, previous, args.adopt_existing and not args.check)
    if args.plan_json:
        print(json.dumps({"conflicts": conflicts, "plan": [{k: str(v) if isinstance(v, Path) else v for k, v in item.items()} for item in plan],
                          "manifest": {"version": 1, "source": str(LINK_ROOT), "entries": {i["relative"]: i["expected"] for i in plan}}}))
        return int(bool(conflicts))
    for problem in conflicts:
        print(f"CONFLICT {problem}", file=sys.stderr)
    for item in plan:
        print(f"{'UPDATE' if item['change'] else 'OK'} {item['relative']}")
    if conflicts:
        return 1
    if args.check:
        expected = {"version": 1, "source": str(LINK_ROOT), "entries": {i["relative"]: i["expected"] for i in plan}}
        return int(prior_manifest != expected or any(i["change"] for i in plan))
    if not args.dry_run:
        install(home, plan, manifest)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Install failed: {error}", file=sys.stderr)
        sys.exit(1)
