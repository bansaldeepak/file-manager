# Cleanup UX and Performance Direction

## Reduce the number of decisions

Review folders before individual photos. For example, an import folder containing
1,000 exact copies should need one keeper choice and one confirmed cleanup action.
A folder with 950 duplicates and 50 unique photos should offer moving those 950
copies while preserving the remaining photos.

The current Streamlit implementation provides this workflow in **Folder cleanup**:
protected keeper folder, a filtered overview of every matching folder, checkbox
selection and select-all, and one reviewed batch across multiple folders. Nested
selections are processed once. Optional folder inspection shows six thumbnails
and an exact-match mapping. Batches combine complete-folder quarantine when
eligible with duplicate-image cleanup elsewhere, and show per-folder outcomes.
Complete-folder restoration remains available. Source and kept copies are verified
before any batch moves; shared kept files are hashed once per action.
Unindexed extras block a whole-folder move. No visual-similarity result drives a
folder bulk action.

## Native desktop experience

Continue the Tauri/React/Rust migration in `REQUIREMENTS.md` incrementally:

| Area | Intended behavior |
| --- | --- |
| Overview | Rank folders by duplicate data; show exact, partial, and unresolved coverage. |
| Keeper policy | Let users protect original/reference folders and preview affected copies before applying a policy. |
| Folder review | Show a contact sheet, duplicate/unique counts, retained locations, and one confirmed folder action. |
| Photo review | Virtualize the thumbnail grid; load only visible previews, with a larger comparison when selected. |
| Review queue | Preserve selections across filters and navigation; show one final count and bytes before a batch move. |
| Keyboard | Provide discoverable keep/quarantine/skip shortcuts and advance to the next unresolved group. |
| Recovery | Restore a folder or operation batch in one action, preserving occupied destinations. |
| Progress | Run scanning and verification in background workers with phases, cancellation, and per-file failures. |

Sample previews must be labelled as samples. Exact-copy evidence can support bulk
decisions; similar-photo decisions still require visual review. Quarantine changes
locations and preserves recovery; storage is reclaimed only after confirmed deletion.

## Fast discovery without heavy preview work

Use separate analysis phases: inventory and sizes, inexpensive candidate filtering,
full cryptographic hashes for exact matches, then image decoding and perceptual
analysis as requested. Retain versioned hashes and persistent thumbnail caches.
Bound scan concurrency to avoid saturating a slow external disk. Keep discovery,
preview rendering, and journalled file operations independent.

Czkawka is a useful implementation reference. Its upstream documentation describes
a reusable Rust core, multithreading, shared caches, protected reference paths, and
first/last-4-KB prehash caching. Evaluate `czkawka_core` for discovery during the Rust
milestone; do not assume its image normalization or pHash matches Python ImageHash.
Keep parity tests and the safe file-operation layer as explicit integration gates.

The GTK frontend is now described upstream as legacy; Krokiet is its newer frontend.
The upstream licence notes distinguish MIT core/CLI code from GPL-licensed Slint
frontends. Check the exact dependency revision before adopting code or assets.

## Validation

Measure cold scan, unchanged scan, first folder opening, cached interactions,
verification throughput, and memory separately on the target Mac and representative
external storage. A faster list-only tool is not a comparable preview benchmark.
Use generated datasets, count actual decodes and work performed, and record timings
before promising latency or throughput. Keep warm interactions independent of
whole-library analysis and preview counts bounded as collection size grows.

## Sources checked

- [Czkawka README](https://github.com/qarmin/czkawka/blob/master/README.md)
- [Shared instructions and reference paths](https://github.com/qarmin/czkawka/blob/master/instructions/Instruction.md)
