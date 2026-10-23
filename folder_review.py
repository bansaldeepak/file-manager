"""Exact-copy folder review, independent of Streamlit and the scan database."""

import hashlib
import os
import stat
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path


IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
                            ".gif", ".heic", ".heif", ".avif"})


def within(path, root):
    return path == root or root in path.parents


def identity(path):
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.resolve() != path:
        raise ValueError(f"Not a regular file without symlink ancestors: {path}")
    return (metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def hash_regular_file(path):
    before = identity(path)
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        opened = (metadata.st_dev, metadata.st_ino, metadata.st_size,
                  metadata.st_mtime_ns, metadata.st_ctime_ns)
        if opened != before:
            raise ValueError(f"File changed before verification: {path}")
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if identity(path) != before:
        raise ValueError(f"File changed during verification: {path}")
    return digest.hexdigest()


@dataclass(frozen=True)
class FolderSummary:
    folder: Path
    images: int
    duplicates: int
    duplicate_bytes: int
    keeper_folders: tuple = ()


@dataclass(frozen=True)
class FileMatch:
    source: Path
    keeper: Path
    sha256: str
    source_identity: tuple
    keeper_identity: tuple


@dataclass(frozen=True)
class FolderPlan:
    root: Path
    folder: Path
    keeper_root: Path
    matches: tuple
    unmatched: tuple
    blockers: tuple
    files: tuple
    duplicate_root: Path | None = None

    @property
    def whole_folder(self):
        return bool(self.matches) and not self.unmatched and not self.blockers

    @property
    def duplicate_bytes(self):
        return sum(match.source_identity[2] for match in self.matches)

    @property
    def remaining_images(self):
        return tuple(path for path in self.unmatched if path.suffix.lower() in IMAGE_SUFFIXES)


def indexed_folders(rows, root):
    root = Path(root).resolve()
    folders = defaultdict(list)
    for row in rows:
        path = Path(row[0])
        if not within(path, root):
            continue
        parent = path.parent
        while parent != root:
            folders[parent].append(row)
            parent = parent.parent
    return folders


def reference_index(rows, keeper_root):
    keeper_root = Path(keeper_root).resolve()
    by_hash = defaultdict(list)
    for row in rows:
        if row[3] and not row[8] and within(Path(row[0]), keeper_root):
            by_hash[(row[3], row[1])].append(row)
    for candidates in by_hash.values():
        candidates.sort(key=lambda row: row[0])
    return by_hash


def validate_duplicate_scope(root, keeper_root, duplicate_root=None):
    root = Path(root).resolve()
    keeper_root = Path(keeper_root)
    if keeper_root.resolve() != keeper_root or keeper_root == root or not within(keeper_root, root):
        raise ValueError("Choose an original subfolder within the scanned source, without symlinks.")
    if duplicate_root is None:
        return None
    duplicate_root = Path(duplicate_root)
    if (duplicate_root.resolve() != duplicate_root or duplicate_root == root
            or not within(duplicate_root, root)):
        raise ValueError("Choose a duplicate subfolder within the scanned source, without symlinks.")
    if within(duplicate_root, keeper_root) or within(keeper_root, duplicate_root):
        raise ValueError("Original and duplicate folders must not overlap.")
    if not duplicate_root.is_dir():
        raise ValueError("The selected duplicate folder is no longer available.")
    return duplicate_root


def folder_summaries(rows, root, keeper_root, duplicate_root=None):
    duplicate_root = validate_duplicate_scope(root, keeper_root, duplicate_root)
    keeper_root = Path(keeper_root).resolve()
    references = reference_index(rows, keeper_root)
    locations = {key: Path(candidates[0][0]).parent for key, candidates in references.items()}
    summaries = []
    for folder, members in indexed_folders(rows, root).items():
        if duplicate_root is not None and not within(folder, duplicate_root):
            continue
        # A cleanup action may neither contain nor be inside the kept folder.
        if within(folder, keeper_root) or within(keeper_root, folder):
            continue
        duplicates = [row for row in members if row[3] and not row[8]
                      and (row[3], row[1]) in references]
        if duplicates:
            kept_counts = defaultdict(int)
            for row in duplicates:
                kept_counts[locations[(row[3], row[1])]] += 1
            summaries.append(FolderSummary(folder, len(members), len(duplicates),
                                           sum(row[1] for row in duplicates),
                                           tuple(sorted(kept_counts.items(), key=lambda item: str(item[0])))))
    return sorted(summaries, key=lambda summary: (-summary.duplicate_bytes, str(summary.folder)))


def inventory(folder):
    files, blockers = [], []

    def failed(error):
        raise error

    for directory, dirs, names in os.walk(folder, followlinks=False, onerror=failed):
        base = Path(directory)
        for name in list(dirs):
            path = base / name
            if path.is_symlink():
                blockers.append(path)
                dirs.remove(name)
        for name in names:
            path = base / name
            metadata = path.lstat()
            if stat.S_ISREG(metadata.st_mode) and path.resolve() == path:
                files.append(path)
            else:
                blockers.append(path)
    return tuple(sorted(files)), tuple(sorted(blockers))


def plan_folder(rows, root, folder, keeper_root, *, references=None, indexed=None, duplicate_root=None):
    root = Path(root).resolve()
    folder = Path(folder)
    keeper_root = Path(keeper_root)
    duplicate_root = validate_duplicate_scope(root, keeper_root, duplicate_root)
    if duplicate_root is not None and not within(folder, duplicate_root):
        raise ValueError("Cleanup folder is outside the selected duplicate folder.")
    if folder.resolve() != folder or keeper_root.resolve() != keeper_root:
        raise ValueError("Choose real folders, not symlinks.")
    if folder == root or not within(folder, root) or not within(keeper_root, root):
        raise ValueError("Choose separate subfolders within the scanned source.")
    if within(folder, keeper_root) or within(keeper_root, folder):
        raise ValueError("The kept folder and cleanup folder must not overlap.")
    if not folder.is_dir() or not keeper_root.is_dir():
        raise ValueError("Both folders must still exist.")
    files, blockers = inventory(folder)
    if references is None:
        references = reference_index(rows, keeper_root)
    if indexed is None:
        indexed = {row[0]: row for row in rows}
    matches, unmatched = [], []
    for path in files:
        row = indexed.get(str(path))
        if row is None or not row[3] or row[8]:
            unmatched.append(path)
            continue
        source_stat = path.stat()
        if (source_stat.st_size, source_stat.st_mtime) != (row[1], row[2]):
            unmatched.append(path)
            continue
        keeper = None
        for candidate in references.get((row[3], row[1]), []):
            candidate_path = Path(candidate[0])
            try:
                keeper_identity = identity(candidate_path)
                keeper_stat = candidate_path.stat()
            except (OSError, ValueError):
                continue
            if (keeper_stat.st_size, keeper_stat.st_mtime) == (candidate[1], candidate[2]):
                keeper = candidate_path
                break
        if keeper is None:
            unmatched.append(path)
        else:
            matches.append(FileMatch(path, keeper, row[3], identity(path), keeper_identity))
    return FolderPlan(root, folder, keeper_root, tuple(matches), tuple(unmatched), blockers, files, duplicate_root)


def collapse_folder_selection(paths):
    selected = []
    for path in sorted(set(paths), key=lambda p: (len(p.parts), str(p))):
        if not any(within(path, parent) for parent in selected):
            selected.append(path)
    return selected


def plan_folders(rows, root, selected, keeper_root, duplicate_root=None):
    """Prepare a disjoint batch with a single shared index lookup."""
    references = reference_index(rows, keeper_root)
    indexed = {row[0]: row for row in rows}
    return [plan_folder(rows, root, folder, keeper_root, references=references, indexed=indexed,
                        duplicate_root=duplicate_root)
            for folder in collapse_folder_selection(selected)]


def require_image_retention(plan, allow_empty=False):
    if not plan.remaining_images and not allow_empty:
        raise ValueError(f"{plan.folder} will have no images left. Explicitly acknowledge this before moving all its images; "
                         f"exact kept copies must remain in {plan.keeper_root}.")


def select_folder_copies(plans, paths):
    """Restrict a reviewed batch to chosen copies, retaining unchecked images."""
    selected = {Path(path) for path in paths}
    available = {match.source for plan in plans for match in plan.matches}
    if not selected or not selected <= available:
        raise ValueError("Select current reviewed copies only. Refresh the folder review if its files changed.")
    result = []
    for plan in plans:
        chosen = tuple(match for match in plan.matches if match.source in selected)
        if chosen:
            retained = tuple(sorted((*plan.unmatched, *(match.source for match in plan.matches
                                                       if match.source not in selected))))
            result.append(replace(plan, matches=chosen, unmatched=retained))
    return result


def remaining_folder_plans(plans, moved):
    """Continue a thumbnail review after removing successfully moved copies."""
    moved = {Path(path) for path in moved}
    return [replace(plan, matches=tuple(match for match in plan.matches if match.source not in moved),
                    files=tuple(path for path in plan.files if path not in moved))
            for plan in plans if any(match.source not in moved for match in plan.matches)]


def verify_plan(plan, whole_folder=False, progress=None, verified=None):
    if not plan.matches:
        raise ValueError("No exact duplicates are available to quarantine.")
    duplicate_root = validate_duplicate_scope(plan.root, plan.keeper_root, plan.duplicate_root)
    if duplicate_root is not None and not within(plan.folder, duplicate_root):
        raise ValueError("Cleanup folder is outside the selected duplicate folder.")
    if plan.folder.resolve() != plan.folder or plan.keeper_root.resolve() != plan.keeper_root:
        raise ValueError("A reviewed folder was replaced or redirected.")
    if within(plan.folder, plan.keeper_root) or within(plan.keeper_root, plan.folder):
        raise ValueError("The kept folder must stay outside the cleanup folder.")
    if whole_folder:
        files, blockers = inventory(plan.folder)
        if not plan.whole_folder or blockers or files != plan.files:
            raise ValueError("The folder contains unique, unindexed, changed, or unsafe files. Refresh its review.")
    if verified is None:
        verified = {}
    for index, match in enumerate(plan.matches, 1):
        if not within(match.source, plan.folder) or not within(match.keeper, plan.keeper_root):
            raise ValueError("A reviewed file is outside its expected folder.")
        for path, expected in ((match.source, match.source_identity), (match.keeper, match.keeper_identity)):
            if identity(path) != expected:
                raise ValueError(f"A reviewed file changed. Scan / refresh first: {path}")
            if path not in verified:
                verified[path] = hash_regular_file(path)
            if verified[path] != match.sha256:
                raise ValueError(f"Content no longer matches the indexed exact copy. Scan / refresh: {path}")
        if progress:
            progress(index, len(plan.matches))
    # Protect shared keeper files even if a later verification took a long time.
    for match in plan.matches:
        if identity(match.source) != match.source_identity or identity(match.keeper) != match.keeper_identity:
            raise ValueError("A file changed before the move. Refresh the folder review.")


def move_directory(source, destination):
    """Reserve an empty destination and rename on the same filesystem only."""
    if source.is_symlink() or source.resolve() != source or not source.is_dir():
        raise ValueError("The source must be a real directory.")
    if source == destination or within(destination, source) or within(source, destination):
        raise ValueError("Source and destination directories must not overlap.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.resolve() != destination.parent:
        raise ValueError("The destination contains a symlink.")
    if source.stat().st_dev != destination.parent.stat().st_dev:
        raise ValueError("Whole-folder moves require the same volume. Use duplicate-image cleanup instead.")
    destination.mkdir()  # Exclusive reservation; an existing folder is never merged.
    try:
        os.rename(source, destination)
    except Exception:
        # Remove only our empty reservation, never existing contents.
        try:
            destination.rmdir()
        except OSError:
            pass
        raise
