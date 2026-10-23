# Project Memory

<!-- brief:memory-harness -->
Use `brief memory` commands instead of reading files directly:
- `brief memory list` — concise index of all memories
- `brief memory show <name>` — view a specific memory
- `brief memory create <name> --memtype=<type>` — create a new memory
- `brief memory update <name>` — update an existing memory

Do NOT read `documentation/memory/*.md` files directly — use the commands above.
<!-- /brief:memory-harness -->


## Review performance (2026-10-22)

- A 30,188-row index took approximately 43 seconds to build visual groups at
  threshold 6. The previous Streamlit tab/expander layout prepared about 27,000
  previews across all categories on every widget rerun.
- `app.py` now renders only one category and a bounded page. Review forms avoid
  reruns for each selection. Compressed thumbnails use a bounded metadata-keyed
  cache. Session snapshots reuse groups; moves rebuild only affected visual
  components, including splits when a bridge member is removed.
- Quarantine movement uses one index connection/commit and one history write per
  confirmed batch. Database/WAL timestamps invalidate snapshots after external
  index writes; explicit reload and scan controls remain available.
- Preserve SHA-256, EXIF-corrected RGBA pixel hashing, 64-bit pHash, threshold 6,
  connected-component grouping, and resolution/file-size/path keeper ordering.
- Verification: 15 tests and Python compilation passed. Default-threshold
  visual groups matched the legacy implementation across all 30,188 index
  rows. First visual grouping measured 23.3 seconds versus 43.7 seconds for
  legacy; ordinary review reuses the result. Live browser verification was
  unavailable, so interaction checks used Streamlit AppTest.
- Run `.venv/bin/python -m unittest discover -s tests -v`. Generated fixtures
  cover performance regressions and file operations; never benchmark mutations
  against personal media. `AGENTS.md` is protected from modification by the
  owner's instruction in this conversation.

## Folder cleanup UX (2026-10-22)

- Owner requested folder-level actions: quarantine a complete folder when it
  is fully duplicated; otherwise quarantine its duplicate images and leave
  unique files in place. Source: explicit clarification in this conversation.
- Folder cleanup must preserve verified exact copies outside the selected
  cleanup folder. Visual similarity alone is insufficient for folder bulk
  actions. Show retained locations, file counts, bytes, and bounded thumbnails.
- Czkawka's upstream documentation describes a reusable Rust core, multithreaded
  algorithms, caches, and protected reference folders. Use those ideas for the
  planned native app while retaining this app's image-detection parity rules.
- Implemented **Folder cleanup** with a protected keeper folder, cached indexed
  summaries, six sample thumbnails, source/keeper mappings, and bulk actions.
  Whole-folder moves require every file to be covered by indexed exact copies
  and a same-volume rename. Otherwise move verified duplicate images and leave
  unmatched/unindexed files and unsafe paths. Unindexed sidecars block a whole
  folder move even if a copy might exist elsewhere.
- `folder_review.py` holds the UI-independent planner and verification. Both
  copies are hashed before bulk actions; changing files or overlapping roots
  block the operation. Prepared folder records support whole-folder restoration
  and correct individual restoration after a quarantine-directory collision.
- The JSON history writer uses a shared in-process lock so concurrent Streamlit
  sessions cannot erase each other's recovery records. Native migration should
  replace this with the specified SQLite operation journal.
- Verification: 31 tests passed using disposable fixtures, including complete
  and partial folder actions, changed keepers, concurrent history writers,
  collisions, and interrupted completion logging. Python compilation passed.
  The native UX/engine direction and upstream sources are in `docs/ux-roadmap.md`.

## Multi-folder overview (2026-10-22)

- Owner requested a list of every folder containing duplicates and relief from
  selecting/reviewing folders one at a time. Folder cleanup now lists all indexed
  exact-match folders outside the chosen keeper in a checkbox table, with path
  and coverage filters, select-all, and one reviewed/confirmed batch.
- Parent-folder counts include descendants. Collapse overlapping selections
  before planning so each file is counted and processed once. The keeper remains
  outside every cleanup folder. Whole-folder eligibility requires an inventory,
  not merely 100% coverage of indexed images.
- Default batch mode combines whole-folder quarantine where eligible with
  duplicate-image cleanup elsewhere; an images-only mode retains directories.
  Optional inspection retains six sample thumbnails and source/keeper mappings.
  The overview uses cached index summaries without inventories or preview loads.
- Build shared index lookups once per batch and hash shared keeper paths once
  during its verification. Verify every selected folder before any movement,
  recheck identities before moves, and report later failures per folder alongside
  successful moves. Changing the batch selection/action invalidates confirmation.
- Verification: Python compilation and all 43 tests passed. Generated fixtures
  cover checkbox row selection, filtered select-all, nested selections, mixed
  whole/partial batches, preflight changes, later move failures, shared hashes,
  and confirmation reset. Streamlit interaction checks used AppTest.

## Nainital empty-folder investigation (2026-10-22)

- Owner reported a folder cleanup moving every image and leaving empty source
  folders, and confirmed the affected folder was Nainital. Read-only history
  inspection identified a 276-image folder batch. At audit time all 276 original
  paths existed again; fresh SHA-256 checks found an exact copy for each outside
  Nainital under Mac/Export. No personal files or production index/history rows
  were modified during investigation.
- Root cause: one `.DS_Store` file blocked whole-folder eligibility, triggering
  image-only fallback. Remaining-file counts included metadata and hid that zero
  images would remain. Reproduced with disposable images and a `.DS_Store` file:
  both the backend safety assertion and Streamlit interaction assertion failed
  before the fix. A separate final-mover keeper-selection assertion also failed.
- Folder previews now separate images staying from other files, show kept-copy
  locations, and require a distinct zero-images acknowledgement. Image-only
  backend actions reject emptying a photo folder by default. The final expected-
  match mover rejects selected keepers before moving any file. Per-image folder
  history now records verified SHA-256 and retained paths; older entries remain
  unchanged. Whole-folder actions retain verification and explicit confirmation.
- Verification: all 48 tests and Python compilation passed. Tests cover zero-
  image blocking, explicit acknowledgement without bypassing keeper checks,
  unindexed unique photos staying, source/keeper audit records, and reset of both
  confirmations when changing the batch action. Related files: `app.py`,
  `folder_review.py`, `tests/test_folder_review.py`. Refresh and scan after
  restoring files outside the app because removed index rows require reindexing.

## Folder match locations and thumbnail choices (2026-10-22)

- Owner showed that a parent keeper such as Mac obscured the exact duplicate
  locations, and that selecting a cleanup folder opened only a bulk table without
  thumbnails or individual-copy choices. Choosing Nainital as keeper must make
  its matching copies elsewhere visible and keep Nainital protected.
- Folder summaries now include indexed kept-copy subfolders and matched-image
  counts. Count one canonical keeper per source image so several kept copies do
  not inflate coverage. Parent-source counts include descendants and selections
  still collapse overlaps. Refresh these summaries when the index changes.
- Review selected folders defaults to thumbnail pairs with source and protected
  paths. Six pairs load per page. Copy choices persist across pages, one confirmed
  action moves all checked copies, and review resumes remaining duplicates without
  reselecting the folder. Unchecked copies are retained in subset plans, so they
  count toward images staying. Folder actions covering all duplicates are a
  separate mode; permanent deletion remains restricted to quarantine review.
- Cache prepared-plan tokens and thumbnails across checkbox reruns. Clear stale
  choices when the review context changes, bind final confirmation to the exact
  chosen paths, retain zero-image acknowledgement, and verify checked copies and
  protected matches before movement. Overview counts remain index-only evidence.
- Verification: all 55 tests and Python compilation passed. Generated fixtures
  cover split keeper locations, bounded pairs, multi-page choices, checked-only
  movement, resumed review, clearing/reset of confirmation, changed keepers,
  zero-image blocking, and existing whole-folder/recovery behavior. Interaction
  verification used Streamlit AppTest; no personal media were moved by the agent.

## Original and optional duplicate folder (2026-10-22)

- Owner requested two selectors: a protected original folder and an optional
  folder to find duplicates in. An empty second selector searches the rest of
  the scanned source. Original descendants and overlapping ancestors must not
  appear as duplicate-folder choices.
- Folder cleanup now shows both selectors side by side. Choosing the second
  folder opens its thumbnail comparison directly, including subfolders. Only
  checked exact copies inside that scope can move. The all-other-folders mode
  retains the overview and multi-folder workflow. Changing either folder resets
  copy choices and confirmations.
- Carry the optional duplicate root in immutable plans, cache keys, and result
  context. Validate its bounds and separation from the original during planning
  and again before movement; batches must share one scope. Preserve an explicit
  scope after it empties or moves instead of silently broadening the search.
- Verification: Python compilation and all 64 tests passed, using disposable
  fixtures and Streamlit AppTest. New checks cover scoped descendants, protected
  overlap rejection, checked-only moves confined to the second folder, original
  and duplicate selection changes, and emptied or removed scope retention.
  No personal media or production cache/history were modified by the agent.

## Native desktop planning (2026-10-22)

- Owner requested Rust desktop planning for early testing, better UI/UX, and
  faster loading. Scope, proposal status, and environment evidence are captured
  in [native desktop planning](memory/native-desktop-planning.md).
- The [draft PRD](documentation/stories/native-desktop/PRD.md) proposes staged
  exact discovery and a read-only desktop preview before cleanup and full photo
  parity. Implementation and performance results remain pending.
