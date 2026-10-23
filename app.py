import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
from collections import defaultdict
from pathlib import Path

import imagehash
import streamlit as st
from PIL import Image, ImageOps

from folder_review import (
    IMAGE_SUFFIXES, collapse_folder_selection, folder_summaries, identity, indexed_folders, inventory,
    move_directory, plan_folder, plan_folders, remaining_folder_plans, require_image_retention,
    select_folder_copies, verify_plan, within,
)

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "dedupe_cache.sqlite3"
DECISIONS_PATH = APP_DIR / "review_decisions.json"
SUPPORTED = IMAGE_SUFFIXES

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime REAL NOT NULL,
            sha256 TEXT, pixel_hash TEXT, width INTEGER, height INTEGER,
            phash TEXT, error TEXT, scanned_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def signatures(path):
    with Image.open(path) as im:
        im.seek(0)
        im = ImageOps.exif_transpose(im).convert("RGBA")
        w, h = im.size
        pix = hashlib.sha256(w.to_bytes(8, "big") + h.to_bytes(8, "big") + im.tobytes()).hexdigest()
        ph = str(imagehash.phash(im.convert("RGB"), hash_size=8))
        return w, h, pix, ph

def list_images(root):
    paths = []
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "__pycache__"}]
        for name in files:
            p = Path(dp) / name
            if p.suffix.lower() in SUPPORTED and not p.is_symlink():
                paths.append(p)
    return paths

def scan(root, bar, status):
    paths = list_images(root)
    conn = connect_db()
    cur = conn.cursor()
    errors = 0
    for i, p in enumerate(paths, 1):
        try:
            stat = p.stat()
            old = cur.execute("SELECT size,mtime FROM images WHERE path=?", (str(p),)).fetchone()
            if old and old[0] == stat.st_size and old[1] == stat.st_mtime:
                pass
            else:
                try:
                    sha = file_sha256(p)
                    w, h, pix, ph = signatures(p)
                    err = None
                except Exception as e:
                    sha = pix = ph = w = h = None
                    err = f"{type(e).__name__}: {e}"
                    errors += 1
                cur.execute("""INSERT OR REPLACE INTO images
                    (path,size,mtime,sha256,pixel_hash,width,height,phash,error,scanned_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (str(p), stat.st_size, stat.st_mtime, sha, pix, w, h, ph, err, time.time()))
        except OSError as e:
            errors += 1
        if i % 20 == 0 or i == len(paths):
            conn.commit()
            bar.progress(i / max(len(paths), 1))
            status.text(f"Processed {i:,} / {len(paths):,} images")
    conn.commit()
    conn.close()
    return len(paths), errors

def fetch_rows(root):
    conn = connect_db()
    prefix = str(Path(root).resolve()).rstrip(os.sep) + os.sep
    rows = conn.execute("""SELECT path,size,mtime,sha256,pixel_hash,width,height,phash,error
                           FROM images WHERE path LIKE ? ESCAPE '\\' ORDER BY path""",
                        (prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",)).fetchall()
    conn.close()
    return rows

def grouped(rows, col):
    d = defaultdict(list)
    for r in rows:
        if r[col]:
            d[r[col]].append(r)
    return [g for g in d.values() if len(g) > 1]

def ham(a, b):
    a = int(a, 16) if isinstance(a, str) else a
    b = int(b, 16) if isinstance(b, str) else b
    return (a ^ b).bit_count()

class BKNode:
    def __init__(self, value, item):
        self.value, self.items, self.children = value, [item], {}
class BKTree:
    def __init__(self): self.root = None
    def add(self, value, item):
        value = int(value, 16) if isinstance(value, str) else value
        if self.root is None:
            self.root = BKNode(value, item); return
        n = self.root
        while True:
            d = (value ^ n.value).bit_count()
            if d == 0: n.items.append(item); return
            if d not in n.children: n.children[d] = BKNode(value, item); return
            n = n.children[d]
    def search(self, value, radius):
        value = int(value, 16) if isinstance(value, str) else value
        if self.root is None: return []
        out, stack = [], [self.root]
        while stack:
            n = stack.pop()
            d = (value ^ n.value).bit_count()
            if d <= radius: out.extend(n.items)
            for edge, child in n.children.items():
                if d-radius <= edge <= d+radius: stack.append(child)
        return out

def perceptual_groups(rows, radius):
    valid = [r for r in rows if r[7] and not r[8]]
    tree = BKTree()
    parent = list(range(len(valid)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a != b: parent[b]=a
    first_by_hash = {}
    for i,r in enumerate(valid):
        value = int(r[7], 16)
        if value in first_by_hash:
            union(i, first_by_hash[value])
            continue
        for j in tree.search(value, radius):
            union(i,j)
        tree.add(value,i)
        first_by_hash[value] = i
    d=defaultdict(list)
    for i,r in enumerate(valid): d[find(i)].append(r)
    return [g for g in d.values() if len(g)>1]

def fmt_size(n):
    n = int(n or 0)
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024 or unit == "TB":
            return f"{n} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def thumb(path):
    stat = Path(path).stat()
    return cached_thumb(str(path), stat.st_size, stat.st_mtime_ns)

@st.cache_data(max_entries=256, show_spinner=False)
def cached_thumb(path, size, mtime_ns):
    with Image.open(path) as im:
        im.seek(0)
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((520,520))
        buffer = io.BytesIO()
        im.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()

def load_json(path, default):
    try: return json.loads(path.read_text()) if path.exists() else default
    except Exception: return default

def append_log(entry):
    append_logs([entry])

def append_logs(entries):
    if not entries:
        return
    with history_lock(str(DECISIONS_PATH)):
        write_history(entries)

@st.cache_resource(show_spinner=False)
def history_lock(path):
    # All browser sessions in this Streamlit process share the journal lock.
    return threading.RLock()

def write_history(entries):
    # Do not discard existing history if it cannot be read.
    items = json.loads(DECISIONS_PATH.read_text()) if DECISIONS_PATH.exists() else []
    if not isinstance(items, list):
        raise ValueError("Action history must contain a list.")
    items.extend(entries)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=APP_DIR,
                                         prefix=".review-decisions-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(items, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(DECISIONS_PATH)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def quarantine_root(source_root):
    # Sibling folder, not inside the scan root, so it will not be re-scanned.
    return source_root.parent / f"{source_root.name}_Duplicate_Quarantine"

def unique_destination(path):
    if not path.exists(): return path
    stamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.stem}__duplicate_{stamp}{path.suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}__duplicate_{stamp}_{counter}{path.suffix}")
        counter += 1
    return candidate

def move_to_quarantine(src, root):
    src = Path(src)
    root = Path(root).resolve()
    # Require a file within the selected source root.
    src_resolved = src.resolve()
    try: rel = src_resolved.relative_to(root)
    except ValueError: raise ValueError(f"Refusing to move file outside source folder: {src}")
    qroot = quarantine_root(root)
    dst = unique_destination(qroot / rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst

def restore_from_quarantine(qpath, qroot, original_root):
    qpath = Path(qpath).resolve()
    qroot = Path(qroot).resolve()
    try: rel = qpath.relative_to(qroot)
    except ValueError: raise ValueError("File is outside the quarantine folder.")
    original_root = Path(original_root).resolve()
    original = original_root / rel
    # A complete-folder collision can rename its quarantine directory. Recover
    # the true source path from the prepared folder manifest in that case.
    for entry in folder_recovery_records(original_root, qroot):
        folder = Path(entry["to"])
        if within(qpath, folder):
            relative = qpath.relative_to(folder)
            if any(Path(f["relative"]) == relative for f in entry["files"]):
                original = Path(entry["from"]) / relative
                break
    dst = unique_destination(original)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(qpath), str(dst))
    return dst

def walk_quarantine(qroot):
    out=[]
    if qroot.exists():
        for dp, dirs, files in os.walk(qroot):
            for name in files:
                p=Path(dp)/name
                if p.suffix.lower() in SUPPORTED:
                    out.append(p)
    return sorted(out)

def index_stamp():
    # Also notice commits from another browser session or an external scanner.
    paths = (DB_PATH, Path(f"{DB_PATH}-wal"))
    stamps = []
    for path in paths:
        try:
            stat = path.stat()
            stamps.append((stat.st_mtime_ns, stat.st_size))
        except FileNotFoundError:
            stamps.append(None)
    return tuple(stamps)

class ReviewSnapshot:
    def __init__(self, root, rows, stamp):
        self.root = root
        self.rows = rows
        self.stamp = stamp
        self.groups = {}

    def get_groups(self, category, threshold):
        key = (category, threshold if category == "visual" else None)
        if key not in self.groups:
            # Keep only the current visual threshold to bound session memory.
            if category == "visual":
                self.groups = {k: v for k, v in self.groups.items() if k[0] != "visual"}
                self.groups[key] = perceptual_groups(self.rows, threshold)
            else:
                self.groups[key] = grouped(self.rows, 3 if category == "byte" else 4)
        return self.groups[key]

    def remove_paths(self, paths):
        paths = set(paths)
        self.rows = [r for r in self.rows if r[0] not in paths]
        for (category, threshold), groups in self.groups.items():
            updated = []
            for group in groups:
                if not any(r[0] in paths for r in group):
                    updated.append(group)
                    continue
                remaining = [r for r in group if r[0] not in paths]
                if category == "visual":
                    # Removing a bridge can split a connected component.
                    updated.extend(perceptual_groups(remaining, threshold))
                elif len(remaining) > 1:
                    updated.append(remaining)
            self.groups[(category, threshold)] = updated
        self.stamp = index_stamp()

def quarantine_selected(paths, root, category, progress=None, expected=None):
    moved, failures = [], []
    paths = list(dict.fromkeys(paths))
    if expected is not None:
        selected = {Path(p) for p in paths}
        for item in paths:
            match = expected[item]
            if Path(item) != match.source or match.keeper in selected:
                raise ValueError("A protected keeper is also selected to move, or its source mapping changed. Refresh the review.")
    conn = connect_db()
    try:
        for i, item in enumerate(paths, 1):
            try:
                if expected is not None:
                    match = expected[item]
                    if (identity(match.source) != match.source_identity
                            or identity(match.keeper) != match.keeper_identity):
                        raise ValueError("A reviewed file changed before the move. Scan / refresh first.")
                dest = move_to_quarantine(item, root)
                entry = {"action": "quarantined", "from": item, "to": str(dest),
                         "group": category, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
                if expected is not None:
                    entry.update({"keeper": str(match.keeper), "sha256": match.sha256})
                moved.append(entry)
            except Exception as e:
                failures.append(f"{item}: {e}")
            if progress:
                progress(i, len(paths))
        if moved:
            try:
                append_logs(moved)
            except Exception as e:
                failures.append(f"Files were moved, but action history could not be saved: {e}")
            try:
                conn.executemany("DELETE FROM images WHERE path=?", [(m["from"],) for m in moved])
                conn.commit()
            except Exception as e:
                conn.rollback()
                failures.append(f"Files were moved, but the scan index could not be updated: {e}")
    finally:
        conn.close()
    return moved, failures

def quarantine_folder(plan, progress=None, verified=None):
    verify_plan(plan, whole_folder=True, progress=progress, verified=verified)
    destination = unique_destination(quarantine_root(plan.root) / plan.folder.relative_to(plan.root))
    operation = uuid.uuid4().hex
    prepared = {
        "action": "folder_quarantined", "status": "prepared", "operation_id": operation,
        "from": str(plan.folder), "to": str(destination), "root": str(plan.root),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": [{"relative": str(m.source.relative_to(plan.folder)), "keeper": str(m.keeper),
                   "sha256": m.sha256} for m in plan.matches],
    }
    conn = connect_db()
    failures = []
    try:
        # A durable recovery record must exist before the directory moves.
        append_log(prepared)
        files, blockers = inventory(plan.folder)
        if blockers or files != plan.files or not plan.whole_folder:
            raise ValueError("Folder contents changed. Refresh its review before moving it.")
        for match in plan.matches:
            if (identity(match.source) != match.source_identity
                    or identity(match.keeper) != match.keeper_identity):
                raise ValueError("A file changed after verification. Refresh its review.")
        move_directory(plan.folder, destination)
        try:
            append_log({"action": "folder_quarantined", "status": "completed",
                        "operation_id": operation, "from": str(plan.folder), "to": str(destination),
                        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        except Exception as e:
            failures.append(f"Folder moved; its prepared recovery record remains, but completion could not be logged: {e}")
        try:
            conn.executemany("DELETE FROM images WHERE path=?", [(str(m.source),) for m in plan.matches])
            conn.commit()
        except Exception as e:
            conn.rollback()
            failures.append(f"Folder moved, but the index could not be updated: {e}")
    finally:
        conn.close()
    return destination, failures

def quarantine_folder_images(plan, progress=None, allow_empty=False, move_progress=None):
    require_image_retention(plan, allow_empty=allow_empty)
    verify_plan(plan, progress=progress)
    expected = {str(m.source): m for m in plan.matches}
    return quarantine_selected(expected, plan.root, "Folder cleanup", progress=move_progress, expected=expected)


def quarantine_folder_batch(plans, images_only=False, progress=None, move_progress=None, allow_empty=False):
    if not plans:
        raise ValueError("Select at least one folder with exact copies.")
    root, keeper = plans[0].root, plans[0].keeper_root
    if any(plan.root != root or plan.keeper_root != keeper for plan in plans):
        raise ValueError("All selected folders must share the scanned root and protected keeper.")
    if any(plan.duplicate_root != plans[0].duplicate_root for plan in plans):
        raise ValueError("All selected folders must share the duplicate-search scope.")
    if len(collapse_folder_selection([p.folder for p in plans])) != len(plans):
        raise ValueError("Nested or repeated cleanup folders must be combined before moving.")
    verified = {}
    total = sum(len(plan.matches) for plan in plans)
    completed = 0
    modes = []
    for plan in plans:
        whole = (not images_only and plan.whole_folder
                 and plan.folder.stat().st_dev == root.parent.stat().st_dev)
        if not whole:
            require_image_retention(plan, allow_empty=allow_empty)
        verify_plan(plan, whole_folder=whole, verified=verified,
                    progress=(lambda i, n, offset=completed: progress(offset + i, total)) if progress else None)
        completed += len(plan.matches)
        modes.append(whole)
    # Verification of later folders must not hide changes to earlier ones.
    for plan in plans:
        for match in plan.matches:
            if (identity(match.source) != match.source_identity
                    or identity(match.keeper) != match.keeper_identity):
                raise ValueError("A reviewed copy changed during batch verification. Refresh the review.")
    moved_paths, failures, outcomes = [], [], []
    for position, (plan, whole) in enumerate(zip(plans, modes), 1):
        if move_progress:
            move_progress(position - 1, len(plans))
        try:
            if whole:
                destination, errors = quarantine_folder(plan, verified=verified)
                moved = [str(match.source) for match in plan.matches]
                action = "Complete folder"
            else:
                expected = {str(match.source): match for match in plan.matches}
                moved_entries, errors = quarantine_selected(expected, root, "Folder batch", expected=expected)
                moved = [entry["from"] for entry in moved_entries]
                action = "Duplicate images"
            moved_paths.extend(moved)
            failures.extend(f"{plan.folder}: {error}" for error in errors)
            outcomes.append({"Folder": str(plan.folder), "Action": action,
                             "Kept copies in": str(plan.keeper_root),
                             "Images moved": len(moved), "Status": "Completed" if not errors else "Check errors"})
        except Exception as error:
            failures.append(f"{plan.folder}: {error}")
            outcomes.append({"Folder": str(plan.folder), "Action": "Stopped",
                             "Kept copies in": str(plan.keeper_root),
                             "Images moved": 0, "Status": str(error)})
    if move_progress:
        move_progress(len(plans), len(plans))
    return moved_paths, failures, outcomes

def folder_recovery_records(root, qroot):
    records = load_json(DECISIONS_PATH, [])
    if not isinstance(records, list):
        return []
    prepared = [entry for entry in records if isinstance(entry, dict)
                and entry.get("action") == "folder_quarantined"
                and entry.get("status") == "prepared"]
    result = []
    for entry in prepared:
        if entry.get("root") != str(root):
            continue
        if not isinstance(entry.get("operation_id"), str) or not entry["operation_id"]:
            continue
        try:
            source = Path(entry["from"])
            destination = Path(entry["to"])
            relative_files = [Path(f["relative"]) for f in entry["files"]]
        except (KeyError, TypeError, ValueError):
            continue
        if any(path.is_absolute() or ".." in path.parts for path in relative_files):
            continue
        if (source == root or not within(source, root) or not within(destination, qroot)
                or destination == qroot or destination.resolve() != destination):
            continue
        if destination.is_dir() and any((destination / relative).is_file() for relative in relative_files):
            result.append(entry)
    return result

def restore_folder(entry, root, qroot):
    source = Path(entry["to"])
    original = Path(entry["from"])
    if (source == qroot or not within(source, qroot) or source.resolve() != source
            or original == root or not within(original, root) or original.resolve() != original):
        raise ValueError("Folder recovery paths are outside their trusted roots or contain symlinks.")
    destination = unique_destination(original)
    append_log({"action": "folder_restore_prepared", "from": str(source), "to": str(destination),
                "operation_id": entry["operation_id"], "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    move_directory(source, destination)
    failures = []
    try:
        append_log({"action": "folder_restored", "from": str(source), "to": str(destination),
                    "operation_id": entry["operation_id"], "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as e:
        failures.append(f"Folder restored to {destination}, but completion could not be logged: {e}")
    return destination, failures

def folder_progress(bar, phase):
    last_update = 0

    def update(index, total):
        nonlocal last_update
        now = time.monotonic()
        if index == 1 or index == total or now - last_update >= 0.1:
            bar.progress(index / total, text=f"{phase} {index:,} of {total:,} images")
            last_update = now
    return update

def group_id(group):
    # New metadata must not inherit a confirmation for an older review.
    rows = sorted(group, key=lambda r: r[0])
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]

def render_review(review, root, category, label, threshold):
    with st.spinner("Preparing duplicate groups…"):
        groups = review.get_groups(category, threshold)
    st.subheader(f"{label}: {len(groups):,} groups")
    if not groups:
        st.info("No groups found in this category.")
        return
    st.caption("Suggested keeper: highest resolution, then largest file. Review the selected copies before moving them.")
    page_size = st.selectbox("Groups per page", [1, 5, 10], index=1, key="review_page_size")
    page_count = (len(groups) + page_size - 1) // page_size
    root_id = hashlib.sha256(str(root).encode()).hexdigest()[:12]
    page_key = f"{root_id}_{category}_page"
    st.session_state[page_key] = min(st.session_state.get(page_key, 1), page_count)
    page = st.number_input("Page", min_value=1, max_value=page_count, step=1, key=page_key)
    start = (page - 1) * page_size
    page_groups = groups[start:start + page_size]
    st.caption(f"Groups {start + 1:,}–{start + len(page_groups):,} of {len(groups):,}. After moving, the next groups fill this page.")

    preview_pages = {}
    for gi, group in enumerate(page_groups, start + 1):
        token = group_id(group)
        preview_pages[token] = 1
        if len(group) > 6:
            preview_pages[token] = st.number_input(
                f"Preview page for group {gi}", min_value=1,
                max_value=(len(group) + 5) // 6, step=1,
                key=f"preview_{category}_{token}",
            )
            st.caption("Each preview page shows up to six files. Review every selected copy before confirming.")

    form_id = group_id([r for group in page_groups for r in group])
    with st.form(f"review_{category}_{threshold}_{form_id}"):
        selections = []
        # Only the visible page is decoded, including in collapsed/hidden views.
        for gi, group in enumerate(page_groups, start + 1):
            ordered = sorted(group, key=lambda r: (-(r[5] or 0) * (r[6] or 0), -(r[1] or 0), r[0]))
            token = group_id(group)
            st.markdown(f"**Group {gi}: {len(group):,} files**")
            preview_page = preview_pages[token]
            visible = ordered[(preview_page - 1) * 6:preview_page * 6]
            cols = st.columns(min(3, len(visible)))
            for idx, row in enumerate(visible):
                with cols[idx % len(cols)]:
                    try:
                        st.image(thumb(row[0]), width="stretch")
                    except Exception:
                        st.warning("Preview unavailable")
                    st.markdown(f"**{Path(row[0]).name}**")
                    if row[0] == ordered[0][0]:
                        st.caption("Suggested keeper")
                    st.code(row[0], language=None)
                    st.write(f"Resolution: {row[5] or '?'} × {row[6] or '?'}")
                    st.write(f"File size: {fmt_size(row[1])}")
            options = [r[0] for r in ordered]
            selected = st.multiselect(
                f"Group {gi}: copies to quarantine",
                options=options, default=options[1:],
                format_func=lambda p: f"{Path(p).name}  |  {p}",
                key=f"{category}_selected_{token}",
            )
            selections.append((options, selected))
        confirmed = st.checkbox("I reviewed these groups and want to move only the selected copies to quarantine.")
        submitted = st.form_submit_button("Move selected copies to quarantine", type="primary")
    if submitted:
        selected = list(dict.fromkeys(p for _, chosen in selections for p in chosen))
        if not confirmed:
            st.error("Confirm that you reviewed the selected copies before moving them.")
        elif not selected:
            st.info("Select at least one copy to move.")
        elif any(len(chosen) == len(options) for options, chosen in selections):
            st.error("Keep at least one file in each group. Deselect the copy you want to keep.")
        elif any(chosen and not any(Path(p).is_file() and not Path(p).is_symlink()
                                    for p in options if p not in chosen)
                 for options, chosen in selections):
            st.error("A keeper is missing or no longer a regular image file. Scan / refresh before moving this group.")
        elif index_stamp() != review.stamp:
            st.session_state.pop("review_snapshot", None)
            st.session_state["notice"] = ("The scan index changed. Review the refreshed groups before moving files.", [])
            st.rerun()
        else:
            bar = st.progress(0, text=f"Moving {len(selected)} selected file(s)…")
            try:
                moved, failures = quarantine_selected(
                    selected, root, label,
                    lambda i, total: bar.progress(i / total, text=f"Moved/processed {i} of {total} files"),
                )
            except Exception as e:
                st.error(f"Quarantine failed: {e}")
                return
            review.remove_paths(m["from"] for m in moved)
            st.session_state.pop("quarantine_files", None)
            st.session_state["notice"] = (f"Moved {len(moved)} file(s) to quarantine. No files were permanently deleted.", failures)
            st.rerun()


def folder_comparison_context(root, keeper, duplicate_root=None):
    return (str(root), str(keeper), str(duplicate_root) if duplicate_root is not None else None)


def render_folder_review(review, root):
    st.subheader("Folder cleanup")
    st.write("Protect an original folder, then optionally choose a second folder to search for copies.")
    choices_key = (str(root), review.stamp)
    cached_choices = st.session_state.get("folder_choices")
    if cached_choices is None or cached_choices[0] != choices_key:
        cached_choices = (choices_key, sorted(indexed_folders(review.rows, root), key=str))
        st.session_state["folder_choices"] = cached_choices
    folders = cached_choices[1]
    if not folders:
        st.info("No subfolders are indexed. Scan a source containing your original and duplicate folders.")
        return
    columns = st.columns(2)
    keeper = columns[0].selectbox("Original folder (protected)", folders, index=None,
                                  format_func=lambda p: str(p.relative_to(root)), key="folder_keeper",
                                  help="This folder and all its subfolders are protected from these quarantine actions.")
    duplicate_options = [folder for folder in folders if keeper is not None
                         and not within(folder, keeper) and not within(keeper, folder)]
    choice_key = "folder_duplicate_" + hashlib.sha256(repr((str(root), str(keeper))).encode()).hexdigest()[:12]
    previous = st.session_state.get(choice_key)
    # Keep a previous scope visible after it empties or moves, rather than
    # silently expanding the search to every other folder.
    if (previous is not None and keeper is not None and previous not in duplicate_options
            and within(previous, root) and not within(previous, keeper) and not within(keeper, previous)):
        duplicate_options = sorted([*duplicate_options, previous], key=str)
    duplicate_root = columns[1].selectbox(
        "Find duplicates in (optional)", duplicate_options, index=None, key=choice_key,
        placeholder="All other folders in the source", disabled=keeper is None,
        format_func=lambda p: str(p.relative_to(root)),
        help="Choose one folder (including its subfolders), or leave empty to search the rest of the scanned source. Original folders are excluded.",
    )
    if keeper is None:
        st.info("Select an original folder first. The optional second folder limits where copies can be quarantined.")
        return
    context = folder_comparison_context(root, keeper, duplicate_root)
    st.caption(f"Protected: {keeper.relative_to(root)} and all its subfolders. "
               + (f"Searching only: {duplicate_root.relative_to(root)} and its subfolders. Only copies there can move."
                  if duplicate_root is not None else "Searching all other folders in the scanned source."))
    results = st.session_state.get("folder_batch_results")
    if results and results[0] == context:
        with st.expander("Last batch results", expanded=True):
            st.dataframe(results[1], hide_index=True, width="stretch")
    if duplicate_root is not None and not duplicate_root.is_dir():
        st.info("The selected duplicate folder is no longer present. Choose another folder, or clear the second selection to search all other folders.")
        return
    summaries_key = (*context, review.stamp, "search-scope-v1")
    cached = st.session_state.get("folder_summaries")
    if cached is None or cached[0] != summaries_key:
        try:
            cached = (summaries_key, folder_summaries(review.rows, root, keeper, duplicate_root))
        except ValueError as error:
            st.error(f"Folder comparison unavailable: {error}")
            return
        st.session_state["folder_summaries"] = cached
    summaries = cached[1]
    if not summaries:
        st.info("No indexed exact copies of the originals were found "
                + ("in the selected duplicate folder." if duplicate_root is not None else "in the other source folders."))
        return
    if duplicate_root is not None:
        st.session_state.pop("folder_thumbnail_continue", None)
        batch_key = (summaries_key, (duplicate_root,))
        if st.button("Refresh this comparison"):
            st.session_state.pop("folder_batch_plan", None)
        pending = st.session_state.get("folder_batch_plan")
        if pending is None or pending[0] != batch_key:
            try:
                with st.spinner("Checking this duplicate folder and the protected matches…"):
                    plans = plan_folders(review.rows, root, [duplicate_root], keeper, duplicate_root)
                if not plans[0].matches:
                    st.info("No current exact copies are available in this folder. Scan / refresh if its files changed.")
                    return
                pending = (batch_key, plans)
                st.session_state["folder_batch_plan"] = pending
            except (OSError, ValueError) as error:
                st.error(f"Folder comparison unavailable: {error}")
                return
        render_folder_batch(review, root, keeper, batch_key, pending[1])
        return
    st.caption("All folders with indexed exact copies in the keeper are listed below, largest duplicate data first. Parent-folder counts include subfolders. Changing filters resets selections.")
    query = st.text_input("Filter folder paths", key="folder_filter").strip().casefold()
    complete_only = st.checkbox("Only folders where every indexed image has a kept copy")
    shown = [s for s in summaries if query in str(s.folder.relative_to(root)).casefold()
             and (not complete_only or s.duplicates == s.images)]
    if not shown:
        st.info("No duplicate folders match these filters.")
        return
    table_token = hashlib.sha256(repr((summaries_key, query, complete_only)).encode()).hexdigest()[:16]
    select_all = st.checkbox("Select all shown folders", key=f"folder_select_all_{table_token}")
    continuation = st.session_state.get("folder_thumbnail_continue")
    continuing = bool(continuation and continuation[0] == (*context, review.stamp))
    continuing_folders = {p.folder for p in continuation[1]} if continuing else set()
    checked_context = (table_token, select_all)
    if continuing:
        st.session_state["folder_thumbnail_checked"] = (checked_context, continuing_folders)
    checked_defaults = st.session_state.get("folder_thumbnail_checked")
    default_folders = checked_defaults[1] if checked_defaults and checked_defaults[0] == checked_context else set()
    records = [{"Select": select_all or s.folder in default_folders, "Folder": str(s.folder.relative_to(root)),
                "Duplicate images": s.duplicates, "Indexed images": s.images,
                "Images without a kept match": s.images - s.duplicates,
                "Duplicate data": fmt_size(s.duplicate_bytes),
                "Kept-copy folders (indexed)": "; ".join(f"{path.relative_to(root)} ({count:,})"
                                                          for path, count in s.keeper_folders)} for s in shown]
    edited = st.data_editor(
        records, hide_index=True, width="stretch", height=min(520, 38 + 35 * len(shown)),
        disabled=[name for name in records[0] if name != "Select"],
        column_config={"Select": st.column_config.CheckboxColumn("Select", required=True),
                       "Kept-copy folders (indexed)": st.column_config.TextColumn(
                           width="large", help="Exact-match locations inside the protected folder, with matched-image counts. Verified before moving."),
                       "Indexed images": st.column_config.NumberColumn(
                           help="Scan counts exclude sidecars and unindexed files. Whole-folder eligibility is checked during review.")},
        key=f"folder_table_{table_token}_{select_all}",
    )
    selected = collapse_folder_selection([s.folder for s, row in zip(shown, edited) if row["Select"]])
    checked_count = sum(bool(row["Select"]) for row in edited)
    selected_summaries = [s for s in shown if s.folder in selected]
    st.caption(f"Showing {len(shown):,} of {len(summaries):,} folders. Selected: {len(selected):,} independent folders, "
               f"{sum(s.duplicates for s in selected_summaries):,} indexed duplicate images "
               f"({fmt_size(sum(s.duplicate_bytes for s in selected_summaries))}).")
    if checked_count > len(selected):
        st.info(f"{checked_count - len(selected):,} nested selections are covered by their selected parent folders and will be processed once.")
    batch_key = (summaries_key, tuple(selected))
    if continuing and set(selected) == continuing_folders:
        st.session_state["folder_batch_plan"] = (batch_key, continuation[1])
        st.session_state.pop("folder_thumbnail_continue", None)
    if st.button("Review selected folders", disabled=not selected, type="primary"):
        st.session_state.pop("folder_batch_plan", None)
        try:
            with st.spinner("Checking selected folders and their kept copies…"):
                plans = plan_folders(review.rows, root, selected, keeper)
                if any(not p.matches for p in plans):
                    raise ValueError("A selected folder has no current exact copies. Scan / refresh before reviewing again.")
            st.session_state["folder_batch_plan"] = (batch_key, plans)
        except (OSError, ValueError) as error:
            st.error(f"Batch review unavailable: {error}")
    pending = st.session_state.get("folder_batch_plan")
    if pending and pending[0] == batch_key:
        render_folder_batch(review, root, keeper, batch_key, pending[1])
    st.divider()
    summary = st.selectbox("Inspect a folder (optional)", summaries, index=None,
                           format_func=lambda s: str(s.folder.relative_to(root)),
                           key=f"folder_inspect_{table_token}")
    if summary is not None:
        render_folder_details(review, root, keeper, summaries_key, summary)


def render_folder_batch(review, root, keeper, batch_key, plans):
    st.subheader("Review duplicate folder" if plans[0].duplicate_root is not None else "Review selected folders")
    context = hashlib.sha256(repr(folder_comparison_context(root, keeper, plans[0].duplicate_root)).encode()).hexdigest()[:12]
    mode = st.radio("Folder review mode", ["Thumbnails — choose copies", "Folder actions — all duplicates"],
                    horizontal=True, key=f"folder_review_mode_{context}")
    if mode == "Thumbnails — choose copies":
        render_folder_thumbnails(review, root, keeper, batch_key, plans)
        return
    images_only = st.selectbox("Batch action", ["Whole folders when possible; duplicate images otherwise",
                                               "Duplicate images only"]) == "Duplicate images only"
    try:
        preview = [{"Folder": str(p.folder.relative_to(root)),
                    "Action": "Complete folder" if (not images_only and p.whole_folder
                               and p.folder.stat().st_dev == root.parent.stat().st_dev) else "Duplicate images",
                    "Exact copies to move": len(p.matches),
                    "Images staying in source": len(p.remaining_images),
                    "Other files/unsafe paths staying": len(p.unmatched) + len(p.blockers) - len(p.remaining_images),
                    "Duplicate data": fmt_size(p.duplicate_bytes)} for p in plans]
    except OSError as error:
        st.error(f"A selected folder is no longer available: {error}. Refresh the review.")
        return
    st.dataframe(preview, hide_index=True, width="stretch")
    total = sum(len(p.matches) for p in plans)
    size = fmt_size(sum(p.duplicate_bytes for p in plans))
    st.code(f"KEEP ALL ORIGINALS IN: {keeper}", language=None)
    emptied = [p for p in plans if not p.remaining_images]
    if emptied:
        st.warning(f"All images will leave {len(emptied):,} selected folder(s). Exact kept copies remain in {keeper}. "
                   "Image-only cleanup leaves the source folders and any metadata files in place; a complete-folder move removes the source folder.")
        st.write("Folders with no images remaining: " + ", ".join(str(p.folder.relative_to(root)) for p in emptied))
    with st.expander("Folders containing the kept copies"):
        retained = defaultdict(int)
        for plan in plans:
            for match in plan.matches:
                retained[(str(plan.folder.relative_to(root)), str(match.keeper.parent))] += 1
        st.dataframe([{"Cleanup folder": source, "Kept copies in": location, "Exact copies protected": count}
                      for (source, location), count in retained.items()], hide_index=True, width="stretch")
    st.caption("Whole folders move only when every file is covered and a same-volume rename is available. "
               "Other folders keep their unique or unindexed files. Both copies are verified by SHA-256 before the batch moves.")
    token = hashlib.sha256(repr((batch_key, plans, images_only)).encode()).hexdigest()[:16]
    with st.form(f"folder_batch_{token}"):
        confirmed = st.checkbox(f"I reviewed this batch: {len(plans):,} folders, {total:,} exact copies ({size}). Keep all copies in {keeper.name}.")
        acknowledged_empty = (st.checkbox("I understand the listed folders will have no images left; verified copies stay in the keeper folder.")
                              if emptied else False)
        submitted = st.form_submit_button("Quarantine selected folders", type="primary")
    if not submitted:
        return
    if not confirmed:
        st.error("Confirm the selected folders, exact-copy count, and keeper location first.")
        return
    if emptied and not acknowledged_empty:
        st.error("These source folders will have no images left. Confirm that separately, or change the selection/action.")
        return
    if index_stamp() != review.stamp:
        st.error("The index changed. Reload review results and review the selected folders again.")
        return
    bar = st.progress(0, text="Verifying every selected folder before any files move…")
    try:
        moved, failures, outcomes = quarantine_folder_batch(
            plans, images_only=images_only, progress=folder_progress(bar, "Verified"),
            move_progress=folder_progress(bar, "Processed folders"),
            allow_empty=acknowledged_empty,
        )
    except Exception as error:
        st.error(f"Batch stopped before moving files: {error}")
        st.session_state.pop("folder_batch_plan", None)
        return
    review.remove_paths(moved)
    for key in ("folder_summaries", "folder_plan", "folder_batch_plan", "folder_thumbnail_continue", "quarantine_files"):
        st.session_state.pop(key, None)
    st.session_state["folder_batch_results"] = (folder_comparison_context(root, keeper, plans[0].duplicate_root), outcomes)
    st.session_state["notice"] = (f"Quarantined {len(moved):,} duplicate images across {len(plans):,} selected folders. "
                                 "Kept copies remain protected. No files were permanently deleted.", failures)
    st.rerun()


def update_folder_copy_choice(context, path, key):
    current = st.session_state.get("folder_copy_selection")
    if current is None or current[0] != context:
        return
    chosen = set(current[1])
    if st.session_state[key]:
        chosen.add(path)
    else:
        chosen.discard(path)
    st.session_state["folder_copy_selection"] = (context, chosen)


def select_folder_thumbnail_page(context, paths, selected):
    current = st.session_state.get("folder_copy_selection")
    if current is None or current[0] != context:
        return
    chosen = set(current[1])
    for path in paths:
        if selected:
            chosen.add(path)
        else:
            chosen.discard(path)
    st.session_state["folder_copy_selection"] = (context, chosen)
    version = st.session_state.get("folder_copy_widget_version", (context, 0))
    st.session_state["folder_copy_widget_version"] = (context, (version[1] if version[0] == context else 0) + 1)


def render_folder_thumbnails(review, root, keeper, batch_key, plans):
    matches = [match for plan in plans for match in plan.matches]
    snapshot = st.session_state.get("folder_thumbnail_snapshot")
    if snapshot is None or snapshot[0] != batch_key or snapshot[1] is not plans:
        snapshot = (batch_key, plans, hashlib.sha256(repr((batch_key, plans)).encode()).hexdigest()[:16])
        st.session_state["folder_thumbnail_snapshot"] = snapshot
    token = snapshot[2]
    current = st.session_state.get("folder_copy_selection")
    if current is None or current[0] != token:
        current = (token, set())
        st.session_state["folder_copy_selection"] = current
    chosen = current[1]
    st.code(f"PROTECTED: {keeper}", language=None)
    st.caption("Check copies to quarantine. Their exact matches in the protected folder stay. "
               "Selections persist across thumbnail pages; unique files are outside this action.")
    page_count = (len(matches) + 5) // 6
    page = st.number_input("Thumbnail page", min_value=1, max_value=page_count,
                           step=1, key=f"folder_thumb_page_{token}")
    visible = matches[(page - 1) * 6:page * 6]
    version = st.session_state.get("folder_copy_widget_version", (token, 0))
    widget_version = version[1] if version[0] == token else 0
    choices = [(str(match.source), f"folder_copy_{token}_{widget_version}_{hashlib.sha256(str(match.source).encode()).hexdigest()[:12]}")
               for match in visible]
    st.caption(f"Showing {((page - 1) * 6) + 1:,}–{min(page * 6, len(matches)):,} of {len(matches):,} exact copies. "
               f"Checked across all pages: {len(chosen):,}.")
    controls = st.columns(2)
    controls[0].button("Select all copies on this page", on_click=select_folder_thumbnail_page,
                       args=(token, [path for path, _ in choices], True), key=f"thumb_page_select_{token}")
    controls[1].button("Clear this page", on_click=select_folder_thumbnail_page,
                       args=(token, [path for path, _ in choices], False), key=f"thumb_page_clear_{token}")
    for match, (path, key) in zip(visible, choices):
        columns = st.columns(2)
        for column, image_path, label in ((columns[0], match.source, "Copy you can quarantine"),
                                          (columns[1], match.keeper, "Protected exact copy — stays")):
            with column:
                st.markdown(f"**{label}**")
                st.code(str(image_path.relative_to(root)), language=None)
                try:
                    st.image(thumb(image_path), width="stretch")
                except Exception:
                    st.warning("Preview unavailable. Inspect the file before selecting it.")
        st.checkbox(f"Quarantine copy: {match.source.relative_to(root)}", value=path in chosen,
                    key=key, on_change=update_folder_copy_choice, args=(token, path, key))
        st.caption(f"SHA-256 exact match · {fmt_size(match.source_identity[2])}")
        st.divider()
    selected_plans = select_folder_copies(plans, chosen) if chosen else []
    emptied = [plan for plan in selected_plans if not plan.remaining_images]
    if emptied:
        st.warning("Your checked copies include every image in: " +
                   ", ".join(str(plan.folder.relative_to(root)) for plan in emptied) +
                   f". Verified kept copies stay in {keeper}.")
    action_token = hashlib.sha256(repr((token, sorted(chosen))).encode()).hexdigest()[:16]
    with st.form(f"folder_thumb_action_{action_token}"):
        confirmed = st.checkbox(f"I reviewed the {len(chosen):,} checked copies across all pages. Quarantine only these copies; keep every protected match.")
        acknowledged_empty = (st.checkbox("I understand the checked copies will leave the listed folders with no images; protected matches stay.")
                              if emptied else False)
        submitted = st.form_submit_button("Quarantine checked images", type="primary", disabled=not chosen)
    if not submitted:
        return
    if not confirmed:
        st.error("Confirm the checked images and protected matches before moving them.")
        return
    if emptied and not acknowledged_empty:
        st.error("The checked copies will leave these folders with no images. Confirm that separately or uncheck a copy.")
        return
    if index_stamp() != review.stamp:
        st.error("The index changed. Reload review results and review the copies again.")
        return
    bar = st.progress(0, text="Verifying checked copies and their protected matches…")
    try:
        moved, failures, outcomes = quarantine_folder_batch(
            selected_plans, images_only=True, allow_empty=acknowledged_empty,
            progress=folder_progress(bar, "Verified"), move_progress=folder_progress(bar, "Processed folders"),
        )
    except Exception as error:
        st.error(f"Checked-image action stopped: {error}")
        return
    review.remove_paths(moved)
    for key in ("folder_summaries", "folder_plan", "folder_batch_plan", "folder_copy_selection", "quarantine_files"):
        st.session_state.pop(key, None)
    remaining = remaining_folder_plans(plans, moved)
    if remaining:
        st.session_state["folder_thumbnail_continue"] = ((*folder_comparison_context(root, keeper, plans[0].duplicate_root), review.stamp), remaining)
    else:
        st.session_state.pop("folder_thumbnail_continue", None)
    st.session_state["folder_batch_results"] = (folder_comparison_context(root, keeper, plans[0].duplicate_root), outcomes)
    st.session_state["notice"] = (f"Quarantined {len(moved):,} checked images. Unchecked and protected copies stay. "
                                 "Permanent deletion remains a separate quarantine-review action.", failures)
    st.rerun()


def render_folder_details(review, root, keeper, summaries_key, summary):
    plan_key = (summaries_key, str(summary.folder))
    if st.button("Refresh this folder review"):
        st.session_state.pop("folder_plan", None)
    cached_plan = st.session_state.get("folder_plan")
    if cached_plan is None or cached_plan[0] != plan_key:
        try:
            with st.spinner("Checking folder contents and kept copies…"):
                cached_plan = (plan_key, plan_folder(review.rows, root, summary.folder, keeper))
        except (OSError, ValueError) as e:
            st.error(f"Folder review unavailable: {e}")
            return
        st.session_state["folder_plan"] = cached_plan
    plan = cached_plan[1]
    columns = st.columns(4)
    columns[0].metric("Exact duplicate images", len(plan.matches))
    columns[1].metric("Images staying in source", len(plan.remaining_images))
    columns[2].metric("Other files/unsafe paths staying", len(plan.unmatched) + len(plan.blockers) - len(plan.remaining_images))
    columns[3].metric("Duplicate data", fmt_size(plan.duplicate_bytes))
    st.code(f"KEEP: {keeper}\nCLEAN: {plan.folder}", language=None)
    if plan.whole_folder:
        st.success("Every file in this folder has an indexed exact copy in the keeper folder. You can quarantine the complete folder after verification.")
    else:
        st.info("Only verified duplicate images will move. Unique or unindexed files, sidecars, and unsafe paths stay in this folder.")
    if not plan.matches:
        st.warning("No current exact copies are available. Scan / refresh if files have changed.")
        return
    if not plan.remaining_images:
        st.warning(f"All {len(plan.matches):,} images will leave this source folder. Verified exact copies stay in {keeper}. "
                   "Image-only cleanup leaves the folders and any metadata files; a complete-folder move removes the folder.")
    st.caption("Sample previews. The full action is based on SHA-256 equality, independent of filenames or visual similarity.")
    for match in plan.matches[:3]:
        columns = st.columns(2)
        for column, path, label in ((columns[0], match.source, "Copy to quarantine"),
                                    (columns[1], match.keeper, "Kept copy")):
            with column:
                st.caption(f"{label}: {path.name}")
                try:
                    st.image(thumb(path), width="stretch")
                except Exception:
                    st.warning("Preview unavailable")
    with st.expander(f"All {len(plan.matches):,} exact matches and their kept copies"):
        st.dataframe([{"Copy to quarantine": str(m.source.relative_to(plan.folder)),
                       "Kept copy": str(m.keeper.relative_to(keeper))} for m in plan.matches],
                     hide_index=True, width="stretch")
    if plan.unmatched or plan.blockers:
        with st.expander("Files that will stay"):
            st.dataframe([{"Kept in cleanup folder": str(p.relative_to(plan.folder))}
                          for p in (*plan.unmatched, *plan.blockers)], hide_index=True, width="stretch")
    token = hashlib.sha256(repr((plan_key, plan)).encode()).hexdigest()[:16]
    with st.form(f"folder_cleanup_{token}"):
        confirmed = st.checkbox(f"I reviewed this folder action: {len(plan.matches):,} exact copies ({fmt_size(plan.duplicate_bytes)}). Keep all copies in {keeper.name}.")
        acknowledged_empty = (st.checkbox("I understand no images will remain in this cleanup folder; verified copies stay in the keeper folder.")
                              if not plan.remaining_images else False)
        whole = st.form_submit_button("Quarantine complete folder", disabled=not plan.whole_folder, type="primary")
        suffix = "keep remaining images/files" if plan.remaining_images else "leave folders and metadata"
        images_only = st.form_submit_button(f"Quarantine all {len(plan.matches):,} duplicate images; {suffix}")
    if whole or images_only:
        if not confirmed:
            st.error("Confirm the folder, exact-copy count, and keeper location first.")
            return
        if not plan.remaining_images and not acknowledged_empty:
            st.error("This source folder will have no images left. Confirm that separately before moving all its images.")
            return
        if index_stamp() != review.stamp:
            st.error("The index changed. Reload review results before confirming this folder.")
            return
        bar = st.progress(0, text="Verifying exact copies before any files move…")
        progress = folder_progress(bar, "Verified")
        try:
            if whole:
                destination, failures = quarantine_folder(plan, progress)
                moved_paths = [str(m.source) for m in plan.matches]
                message = f"Quarantined the complete folder ({len(moved_paths):,} images): {destination}"
            else:
                moved, failures = quarantine_folder_images(
                    plan, progress=progress, allow_empty=acknowledged_empty,
                    move_progress=folder_progress(bar, "Moved/processed"),
                )
                moved_paths = [m["from"] for m in moved]
                message = (f"Quarantined {len(moved_paths):,} duplicate images from {plan.folder}. "
                           f"Source folders remain in place; kept copies are in {keeper}.")
        except Exception as e:
            st.error(f"Folder action stopped: {e}")
            st.session_state.pop("folder_plan", None)
            return
        review.remove_paths(moved_paths)
        for key in ("folder_summaries", "folder_plan", "folder_batch_plan", "quarantine_files"):
            st.session_state.pop(key, None)
        st.session_state["notice"] = (message, failures)
        st.rerun()


def render_folder_recovery(root, qroot):
    entries = folder_recovery_records(root, qroot)
    if not entries:
        return
    with st.expander("Restore a complete quarantined folder", expanded=True):
        entry = st.selectbox("Quarantined folder", entries,
                             format_func=lambda e: str(Path(e["from"]).relative_to(root)))
        token = entry["operation_id"]
        st.code(f"QUARANTINE: {entry['to']}\nRESTORE TO: {entry['from']}", language=None)
        with st.form(f"restore_folder_{token}"):
            confirmed = st.checkbox("Restore this folder and all remaining files. Preserve any occupied original location.")
            restore = st.form_submit_button("Restore complete folder")
        if restore:
            if not confirmed:
                st.error("Confirm restoration of this folder first.")
                return
            try:
                destination, failures = restore_folder(entry, root, qroot)
            except Exception as e:
                st.error(f"Folder restoration stopped: {e}")
                return
            st.session_state.pop("quarantine_files", None)
            st.session_state["notice"] = (f"Restored folder: {destination}. Scan / refresh to reindex its images.", failures)
            st.rerun()


def render_quarantine(root, qroot):
    st.subheader("Second-stage review")
    st.write("Preview quarantined files, restore them, or explicitly confirm permanent deletion.")
    st.code(str(qroot), language=None)
    render_folder_recovery(root, qroot)
    if st.button("Refresh quarantine list"):
        st.session_state.pop("quarantine_files", None)
    cached = st.session_state.get("quarantine_files")
    if cached is None or cached[0] != str(qroot):
        with st.spinner("Reading quarantine folder…"):
            cached = (str(qroot), walk_quarantine(qroot))
        st.session_state["quarantine_files"] = cached
    files = cached[1]
    if not files:
        st.info("Quarantine is empty.")
        return
    st.write(f"**{len(files):,} quarantined image(s)**")
    selected_q = st.selectbox("Choose a quarantined file to inspect", [str(p) for p in files],
                              format_func=lambda p: str(Path(p).relative_to(qroot)))
    qpath = Path(selected_q)
    if not qpath.is_file():
        st.warning("This file is no longer available. Refresh the quarantine list.")
        return
    try:
        st.image(thumb(qpath), caption=qpath.name, width="content")
    except Exception:
        st.warning("Preview unavailable, but the file can still be restored or deleted.")
    st.code(str(qpath), language=None)
    try:
        with Image.open(qpath) as im:
            st.write(f"Resolution: {im.width} × {im.height}")
        st.write(f"Size: {fmt_size(qpath.stat().st_size)}")
    except Exception as e:
        st.warning(f"File metadata unavailable: {e}")
    # Bind confirmations to this exact path, never to the previous selection.
    token = hashlib.sha256(selected_q.encode()).hexdigest()[:16]
    with st.form(f"quarantine_{token}"):
        restore_confirm = st.checkbox("I want to restore this file to its original relative folder.")
        restore = st.form_submit_button("Restore selected file")
        st.error("Permanent deletion cannot be undone from this app.")
        delete_confirm = st.checkbox("I reviewed this exact file and want to permanently delete it.")
        delete = st.form_submit_button("Permanently delete selected file")
    if restore or delete:
        if restore and not restore_confirm or delete and not delete_confirm:
            st.error("Confirm the selected action for this exact file first.")
            return
        try:
            if restore:
                restored = restore_from_quarantine(qpath, qroot, root)
                append_log({"action": "restored", "from": str(qpath), "to": str(restored),
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                message = f"Restored to {restored}. Scan / refresh to include it in duplicate results again."
            else:
                resolved = qpath.resolve()
                resolved.relative_to(qroot.resolve())
                if not resolved.is_file():
                    raise ValueError("Selected path is not a regular file.")
                resolved.unlink()
                append_log({"action": "permanently_deleted", "path": str(resolved),
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                message = "Quarantined file permanently deleted."
            files.remove(qpath)
            st.session_state["notice"] = (message, [])
            st.rerun()
        except Exception as e:
            st.error(f"Operation failed: {e}")
            st.session_state.pop("quarantine_files", None)


def main():
    st.set_page_config(page_title="Local Image Duplicate Review", layout="wide")
    st.title("Local Image Duplicate Review")
    st.caption("Local-first review workflow. Files are never permanently deleted without a separate confirmation.")
    with st.sidebar:
        st.header("Scan settings")
        root_text = st.text_input("Source folder", str(Path.home() / "Pictures"),
                                  help="Full path to your image library. Subfolders are included.")
        threshold = st.slider("Visual similarity threshold", 0, 16, 6,
                              help="Lower is stricter. Visually similar groups need manual review.")
        scan_button = st.button("Scan / refresh folder", type="primary", width="stretch")
        reload_button = st.button("Reload review results", help="Reload the index and quarantine list without scanning images.")
    if reload_button:
        st.session_state.pop("review_snapshot", None)
        st.session_state.pop("quarantine_files", None)
    if scan_button:
        root = Path(root_text).expanduser()
        if not root.exists() or not root.is_dir():
            st.error("Enter an existing source folder.")
        else:
            bar, status = st.progress(0), st.empty()
            with st.spinner("Scanning locally. Unchanged files use the cache…"):
                count, errors = scan(str(root.resolve()), bar, status)
            st.session_state["active_root"] = str(root.resolve())
            st.session_state.pop("review_snapshot", None)
            st.session_state.pop("quarantine_files", None)
            st.success(f"Scan finished: {count:,} files found, {errors:,} read/decode errors.")
    notice = st.session_state.pop("notice", None)
    if notice:
        st.info(notice[0])
        for failure in notice[1]:
            st.error(failure)
    root = Path(st.session_state.get("active_root", root_text)).expanduser()
    if not root.exists() or not root.is_dir():
        st.info("Enter a valid folder in the sidebar and click Scan / refresh folder.")
        return
    root = root.resolve()
    qroot = quarantine_root(root)
    stamp = index_stamp()
    review = st.session_state.get("review_snapshot")
    if review is None or review.root != str(root) or review.stamp != stamp:
        review = ReviewSnapshot(str(root), fetch_rows(root), stamp)
        st.session_state["review_snapshot"] = review
    st.write(f"**Source:** `{root}`")
    st.write(f"**Indexed images:** {len(review.rows):,}  |  **Quarantine folder:** `{qroot}`")
    st.warning("Quarantine preserves files for later review. Permanent deletion is a separate, confirmed action.")
    view = st.radio("Review category", ["Byte-identical", "Pixel-identical", "Visually similar",
                                       "Folder cleanup", "Quarantine review", "Errors & help"], horizontal=True)
    categories = {"Byte-identical": "byte", "Pixel-identical": "pixel", "Visually similar": "visual"}
    if view in categories:
        render_review(review, root, categories[view], view, threshold)
    elif view == "Folder cleanup":
        render_folder_review(review, root)
    elif view == "Quarantine review":
        render_quarantine(root, qroot)
    else:
        failures = [r for r in review.rows if r[8]]
        st.write(f"Files with scan errors: {len(failures):,}")
        if failures:
            st.dataframe([{"path": r[0], "error": r[8]} for r in failures], width="stretch")
        st.markdown("""
**Match categories**
- **Byte-identical:** SHA-256 of the entire file matches.
- **Pixel-identical:** decoded pixels and dimensions match after EXIF orientation.
- **Visually similar:** perceptual hashes are close; false positives are possible.

**Review**
- Choose a category and page size. Only that page's previews are loaded.
- Selections and confirmation are submitted together. Keep at least one copy per group.
- Quarantine and restore preserve relative folders and avoid overwriting existing destinations.
- Only quarantined files can be permanently deleted, with explicit confirmation.
- Scan results and action history remain local. Reload review results after external changes.
        """)
        if DECISIONS_PATH.exists():
            st.download_button("Download action history", DECISIONS_PATH.read_bytes(),
                               file_name="image_dedupe_action_history.json", mime="application/json")


if __name__ == "__main__":
    main()
