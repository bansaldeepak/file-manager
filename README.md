# Local Image Duplicate Review v2

## Update for current Streamlit
This version uses `width="stretch"` / `width="content"` instead of the deprecated `use_container_width` argument.

## Staged review workflow
1. Scan a local image folder.
2. In each duplicate group, select copies to quarantine. The highest-resolution, then largest-file candidate is suggested as keeper.
3. Confirm the move. Files are moved to a sibling folder named `<source-folder>_Duplicate_Quarantine`, preserving relative directory structure.
4. Use **Quarantine review** to preview each moved image.
5. Restore a file if needed, or explicitly confirm permanent deletion of that one quarantined file.

The app never automatically deletes original source files. Quarantine movement is reversible through the app, subject to filesystem availability. It avoids overwriting destination files by creating a unique suffixed name when needed.

## Install / run
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 if needed.

## Fast review
Choose **Byte-identical**, **Pixel-identical**, or **Visually similar**. Only the
selected category and current page are rendered. Use **Groups per page** to
review 1, 5, or 10 groups at a time; large groups show six previews per preview
page. Keeper suggestions remain unselected by default.

Adjust each group's copies, check the review confirmation, then click
**Move selected copies to quarantine** once for the page. Keep at least one
copy in each group. The next groups fill the page after the move. Submit your
choices before navigating to another page.

Selections are held in a form, thumbnails are cached, and duplicate groups are
reused between interactions. A move updates only affected groups and writes
the index and history in a batch. The first visual-similarity calculation can
still take time on a large library; changing its threshold requires a new
calculation. Quarantine folders are read only when opening quarantine review
or explicitly refreshing its list.

Use **Reload review results** to reload the index without hashing images.
Use **Scan / refresh folder** after adding, changing, or restoring source files.

## Folder cleanup
Open **Folder cleanup** and select **Original folder (protected)**. This folder
and its subfolders stay protected. Optionally select **Find duplicates in** to
compare one second folder, including its subfolders. Its thumbnail review opens
directly, and only copies within that second folder can be quarantined. The
original, its descendants, and overlapping parent folders are excluded from
the second selector. Changing either folder resets copy choices and confirmation.

Leave the second selector empty to search all other folders within the scanned
source. A table lists folders with indexed exact copies in the original, with
image counts and data sizes, largest first. **Kept-copy folders (indexed)** lists the actual matching subfolders and
counts, so selecting a parent such as `Mac` also explains which dated folders
contain the protected copies. Filter by folder path or indexed-image coverage.

Check individual rows or **Select all shown folders**, then click **Review
selected folders**. Nested selections are covered by their selected parent and
processed once. Changing filters resets selections.

An emptied or quarantined second folder remains selected. Choose another folder
or clear the second selector to search elsewhere; the scope never widens automatically.

Review opens **Thumbnails — choose copies** by default. Each pair shows the copy
you can quarantine and its protected exact match, with both paths. Check individual
copies or **Select all copies on this page**. Six pairs load per page; choices
persist across pages. Confirm **Quarantine checked images** to move only your
checked copies across all pages. Unchecked copies and unique files stay, and the
review continues with the remaining duplicates without reselecting the folder.
Permanent deletion remains available only during **Quarantine review**.

For bulk cleanup, switch to **Folder actions — all duplicates**, review the
counts and actions, then confirm **Quarantine selected folders**. Its default
batch action moves complete folders where eligible and duplicate images elsewhere;
**Duplicate images only** preserves source directories. Thumbnail choices apply
to thumbnail mode; folder mode explicitly covers all duplicates in its review.

The overview loads no thumbnails. Plans and thumbnails are cached, and a batch
reuses index lookups and hashes shared kept copies once. Results show completed
folders and any failures.

Review **Images staying in source** separately from other files. A metadata
file such as `.DS_Store` does not mean a photo will remain. When every image
would leave a selected folder, the app shows the affected folders and kept-copy
locations and requires a separate **no images left** acknowledgement. Image-only
cleanup is blocked without it. This acknowledgement never bypasses SHA-256 or
live keeper checks. Per-image folder-action history records the kept path and
verified hash for later auditing.

Use **Inspect a folder (optional)** for sample thumbnail pairs, the full
source/keeper mapping, and separate single-folder actions:

- **Quarantine complete folder** moves the directory in one rename when every
  file has an indexed exact copy in the kept folder. This requires the same
  volume as quarantine. **Quarantine review** can restore the complete folder.
- **Quarantine all duplicate images** moves every verified
  exact duplicate in that folder without a ten-image limit. Unique or unindexed
  files, sidecars, and unsafe paths stay in place.

SHA-256 verification reads the selected images and their kept copies before
any action, with progress shown. All selected folders are verified before a batch
starts moving; a subsequent move failure is reported per folder. Renamed files can match by content. Visual
similarity does not qualify a file for these folder actions. Unindexed extras
block the whole-folder option even if they might have copies elsewhere; use
image-only cleanup or review those extras separately.

Quarantine preserves files and does not itself free disk space. Directory
collisions receive a unique suffix; recovery records retain the original path.
See [the UX roadmap](docs/ux-roadmap.md) for the native desktop direction.

## Verification
With the virtual environment activated, run:

```bash
python -m py_compile app.py folder_review.py
python -m unittest discover -s tests -v
```

Tests use Python's `unittest` and Streamlit's `AppTest`, included with the
existing dependencies. They generate disposable images and databases to check
bounded rendering, cached grouping, confirmation, keeper preservation,
partial failures, filename collisions, quarantine, restore, and deletion.
Folder tests also cover whole-folder moves, partial cleanup, changed files,
protected kept copies, multi-folder selection, shared verification, nested
selections, scoped two-folder comparisons, selection reset, and recovery after
a missing completion log.
They never operate on your photo library.

## Important
- SHA-256 identifies byte-identical files.
- Decoded pixel hashes identify pixel-identical images after EXIF orientation.
- Perceptual hashes identify likely resized/recompressed copies, but can produce false positives.
- Keep a backup of important files. Permanent deletion is irreversible.
# file-manager
