import json
import shutil
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

import app
import folder_review as folders


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class FolderFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dedupe-folders-test-")
        self.addCleanup(self.temp.cleanup)
        self.app_dir = Path(self.temp.name).resolve()
        self.root = self.app_dir / "library"
        self.keep = self.root / "Originals"
        self.clean = self.root / "Imports"
        self.keep.mkdir(parents=True)
        self.clean.mkdir()
        self.rows = []
        for i in range(24):
            original = self.keep / f"original-{i:02d}.png"
            duplicate = self.clean / f"renamed-copy-{i:02d}.png"
            Image.new("RGB", (16, 16), (i * 10, 30, 60)).save(original)
            shutil.copy2(original, duplicate)
            for path in (original, duplicate):
                metadata = path.stat()
                digest = app.file_sha256(path)
                self.rows.append((str(path), metadata.st_size, metadata.st_mtime,
                                  digest, digest, 16, 16, f"{i:016x}", None))
        for name, value in (("APP_DIR", self.app_dir),
                            ("DB_PATH", self.app_dir / "dedupe_cache.sqlite3"),
                            ("DECISIONS_PATH", self.app_dir / "review_decisions.json")):
            self.enterContext(patch.object(app, name, value))
        conn = app.connect_db()
        conn.executemany("INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?)", [(*r, 0) for r in self.rows])
        conn.commit()
        conn.close()

    def plan(self):
        return folders.plan_folder(self.rows, self.root, self.clean, self.keep)

    def add_copy_folder(self, relative, count=2, sidecar=False):
        folder = self.root / relative
        folder.mkdir(parents=True)
        added = []
        for i, original in enumerate(sorted(self.keep.glob("*.png"))[:count]):
            path = folder / f"copy-{i}.png"
            shutil.copy2(original, path)
            metadata = path.stat()
            digest = app.file_sha256(path)
            added.append((str(path), metadata.st_size, metadata.st_mtime,
                          digest, digest, 16, 16, f"{i:016x}", None))
        self.rows.extend(added)
        conn = app.connect_db()
        conn.executemany("INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?)", [(*r, 0) for r in added])
        conn.commit()
        conn.close()
        if sidecar:
            (folder / "notes.txt").write_text("unique notes")
        return folder

    def app_test(self):
        source = APP_PATH.read_text().replace(
            "APP_DIR = Path(__file__).resolve().parent", f"APP_DIR = Path({str(self.app_dir)!r})",
        ).replace('str(Path.home() / "Pictures")', repr(str(self.root)))
        return AppTest.from_string(source, default_timeout=15)


class FolderEngineTests(FolderFixtures):
    def test_optional_scope_searches_only_selected_folder_and_descendants(self):
        other = self.add_copy_folder("Other imports")
        nested = self.add_copy_folder("Other imports/Nested", count=1)
        all_folders = {s.folder for s in folders.folder_summaries(self.rows, self.root, self.keep)}
        self.assertEqual(all_folders, {self.clean, other, nested})
        scoped = folders.folder_summaries(self.rows, self.root, self.keep, other)
        self.assertEqual({s.folder for s in scoped}, {other, nested})
        self.assertEqual(next(s for s in scoped if s.folder == other).duplicates, 3)
        self.assertEqual(folders.folder_summaries(self.rows, self.root, self.keep, None),
                         folders.folder_summaries(self.rows, self.root, self.keep))

    def test_original_and_overlapping_paths_cannot_be_duplicate_scopes(self):
        nested_original = self.add_copy_folder("Originals/Nested", count=1)
        outside = self.app_dir / "outside"
        outside.mkdir()
        for duplicate in (self.keep, nested_original, self.root, outside):
            with self.subTest(duplicate=duplicate):
                with self.assertRaises(ValueError):
                    folders.folder_summaries(self.rows, self.root, self.keep, duplicate)

    def test_summary_explains_matches_spread_across_kept_subfolders(self):
        first = self.keep / "First date"
        second = self.keep / "Second date"
        first.mkdir()
        second.mkdir()
        updates = {}
        for i, original in enumerate(sorted(self.keep.glob("*.png"))):
            destination = (first if i < 12 else second) / original.name
            original.rename(destination)
            updates[str(original)] = str(destination)
        rows = [(updates.get(row[0], row[0]), *row[1:]) for row in self.rows]
        summary = next(s for s in folders.folder_summaries(rows, self.root, self.keep) if s.folder == self.clean)
        self.assertEqual(summary.duplicates, 24)
        self.assertEqual(dict(summary.keeper_folders), {first: 12, second: 12})
        self.assertEqual(sum(n for _, n in summary.keeper_folders), summary.duplicates)

    def test_unique_unindexed_photo_stays_and_history_records_verified_keeper(self):
        unique = self.clean / "unscanned-unique.PNG"
        Image.new("RGB", (32, 32), "white").save(unique)
        plan = self.plan()
        self.assertEqual(plan.remaining_images, (unique,))
        moved, failures = app.quarantine_folder_images(plan)
        self.assertEqual(len(moved), 24)
        self.assertEqual(failures, [])
        self.assertEqual(list(self.clean.iterdir()), [unique])
        records = json.loads(app.DECISIONS_PATH.read_text())
        for entry in records:
            self.assertTrue(folders.within(Path(entry["keeper"]), self.keep))
            self.assertEqual(app.file_sha256(entry["to"]), entry["sha256"])
            self.assertEqual(app.file_sha256(entry["keeper"]), entry["sha256"])

    def test_empty_acknowledgement_does_not_bypass_live_keeper_verification(self):
        plan = self.plan()
        plan.matches[-1].keeper.write_bytes(b"changed keeper")
        with self.assertRaisesRegex(ValueError, "changed"):
            app.quarantine_folder_images(plan, allow_empty=True)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_renamed_files_match_and_whole_folder_has_only_exact_kept_copies(self):
        plan = self.plan()
        self.assertTrue(plan.whole_folder)
        self.assertEqual(len(plan.matches), 24)
        self.assertEqual(plan.unmatched, ())
        self.assertTrue(all(folders.within(m.keeper, self.keep) for m in plan.matches))
        folders.verify_plan(plan, whole_folder=True)

    def test_unique_images_and_unindexed_sidecars_are_kept(self):
        unique = self.clean / "unique.png"
        sidecar = self.clean / "notes.txt"
        Image.new("RGB", (32, 32), "white").save(unique)
        sidecar.write_text("unique notes")
        plan = self.plan()
        self.assertFalse(plan.whole_folder)
        self.assertEqual(set(plan.unmatched), {unique, sidecar})
        folders.verify_plan(plan)
        expected = {str(m.source): m for m in plan.matches}
        moved, failures = app.quarantine_selected(expected, self.root, "Folder cleanup", expected=expected)
        self.assertEqual(len(moved), 24)
        self.assertEqual(failures, [])
        self.assertTrue(unique.exists())
        self.assertEqual(sidecar.read_text(), "unique notes")
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertEqual(len(app.fetch_rows(self.root)), 24)

    def test_changed_keeper_blocks_all_moves(self):
        plan = self.plan()
        keeper = plan.matches[-1].keeper
        keeper.write_bytes(b"replacement content")
        with self.assertRaisesRegex(ValueError, "changed"):
            app.quarantine_folder(plan)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_added_file_blocks_whole_folder_move(self):
        plan = self.plan()
        (self.clean / "new-sidecar.txt").write_text("do not move")
        with self.assertRaisesRegex(ValueError, "contains"):
            app.quarantine_folder(plan)
        self.assertTrue(self.clean.exists())

    def test_file_added_while_preparing_journal_blocks_whole_folder_move(self):
        plan = self.plan()
        original_log = app.append_log

        def changed(entry):
            original_log(entry)
            (self.clean / "new.txt").write_text("concurrent addition")

        with patch.object(app, "append_log", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "contents changed"):
                app.quarantine_folder(plan)
        self.assertTrue(self.clean.exists())

    def test_overlap_and_scan_root_cannot_be_selected_for_cleanup(self):
        for clean, keep in ((self.root, self.keep), (self.clean, self.root),
                            (self.clean, self.clean), (self.root.parent, self.keep)):
            with self.subTest(clean=clean, keep=keep):
                with self.assertRaises(ValueError):
                    folders.plan_folder(self.rows, self.root, clean, keep)

    def test_symlink_contents_block_whole_folder_but_other_duplicates_can_move(self):
        outside = self.app_dir / "outside.txt"
        outside.write_text("outside data")
        link = self.clean / "unsafe.txt"
        link.symlink_to(outside)
        plan = self.plan()
        self.assertFalse(plan.whole_folder)
        self.assertEqual(plan.blockers, (link,))
        with self.assertRaises(ValueError):
            folders.verify_plan(plan, whole_folder=True)
        folders.verify_plan(plan)
        self.assertEqual(outside.read_text(), "outside data")

    def test_stale_hash_is_rejected_even_when_review_metadata_matches(self):
        # Supply a stale cache hash with fresh metadata, to prove content is verified.
        duplicate = Path(self.rows[1][0])
        duplicate.write_bytes(b"new file content")
        metadata = duplicate.stat()
        row = list(self.rows[1])
        row[1:3] = [metadata.st_size, metadata.st_mtime]
        # Make a matching stale-index candidate for the new size too.
        original = list(self.rows[0])
        original[1] = metadata.st_size
        self.rows[0], self.rows[1] = tuple(original), tuple(row)
        # Directly retain the stale digest in a plan with current identity signals.
        match = folders.FileMatch(duplicate, Path(original[0]), row[3],
                                  folders.identity(duplicate), folders.identity(Path(original[0])))
        plan = folders.FolderPlan(self.root, self.clean, self.keep, (match,), (), (), (duplicate,))
        with self.assertRaisesRegex(ValueError, "Content no longer matches"):
            folders.verify_plan(plan)
        self.assertTrue(duplicate.exists())

    def test_full_folder_move_and_collision_safe_folder_restore(self):
        plan = self.plan()
        occupied = app.quarantine_root(self.root) / "Imports"
        occupied.mkdir(parents=True)
        (occupied / "existing.txt").write_text("preserve quarantine")
        with patch.object(app.shutil, "move", side_effect=AssertionError("No per-file moves")):
            destination, failures = app.quarantine_folder(plan)
        self.assertEqual(failures, [])
        self.assertFalse(self.clean.exists())
        self.assertNotEqual(destination, occupied)
        self.assertEqual((occupied / "existing.txt").read_text(), "preserve quarantine")
        self.assertEqual(len(list(destination.glob("*.png"))), 24)
        self.assertEqual(len(app.fetch_rows(self.root)), 24)
        entries = app.folder_recovery_records(self.root, app.quarantine_root(self.root))
        self.assertEqual(len(entries), 1)
        self.clean.mkdir()
        (self.clean / "new.txt").write_text("occupied original")
        restored, failures = app.restore_folder(entries[0], self.root, app.quarantine_root(self.root))
        self.assertEqual(failures, [])
        self.assertNotEqual(restored, self.clean)
        self.assertEqual(len(list(restored.glob("*.png"))), 24)
        self.assertEqual((self.clean / "new.txt").read_text(), "occupied original")
        self.assertEqual(app.folder_recovery_records(self.root, app.quarantine_root(self.root)), [])

    def test_missing_completion_log_still_has_folder_recovery(self):
        original_log = app.append_log

        def fail_completion(entry):
            if entry.get("status") == "completed":
                raise OSError("completion journal unavailable")
            original_log(entry)

        with patch.object(app, "append_log", side_effect=fail_completion):
            destination, failures = app.quarantine_folder(self.plan())
        self.assertTrue(destination.exists())
        self.assertTrue(any("prepared recovery record remains" in f for f in failures))
        self.assertEqual(len(app.folder_recovery_records(self.root, app.quarantine_root(self.root))), 1)

    def test_individual_restore_from_renamed_quarantine_folder_uses_original_location(self):
        qroot = app.quarantine_root(self.root)
        (qroot / "Imports").mkdir(parents=True)
        destination, failures = app.quarantine_folder(self.plan())
        self.assertEqual(failures, [])
        selected = sorted(destination.glob("*.png"))[0]
        restored = app.restore_from_quarantine(selected, qroot, self.root)
        self.assertEqual(restored.parent, self.clean)
        self.assertTrue(restored.exists())
        self.assertEqual(len(list(destination.glob("*.png"))), 23)

    def test_unwritable_prepared_journal_prevents_directory_move(self):
        with patch.object(app, "append_log", side_effect=OSError("history unavailable")):
            with self.assertRaises(OSError):
                app.quarantine_folder(self.plan())
        self.assertTrue(self.clean.exists())
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_concurrent_history_writes_preserve_all_recovery_records(self):
        app.DECISIONS_PATH.write_text("[]")
        original_read = Path.read_text

        def slow_read(path, *args, **kwargs):
            value = original_read(path, *args, **kwargs)
            if path == app.DECISIONS_PATH:
                time.sleep(0.01)  # Force overlapping reads without the journal lock.
            return value

        with patch.object(Path, "read_text", slow_read):
            with ThreadPoolExecutor(max_workers=8) as writers:
                list(writers.map(lambda i: app.append_log({"operation_id": str(i)}), range(8)))
        entries = json.loads(app.DECISIONS_PATH.read_text())
        self.assertEqual({entry["operation_id"] for entry in entries}, {str(i) for i in range(8)})

    def test_restore_completion_failure_reports_successful_destination(self):
        destination, failures = app.quarantine_folder(self.plan())
        self.assertEqual(failures, [])
        entry = app.folder_recovery_records(self.root, app.quarantine_root(self.root))[0]
        original_log = app.append_log

        def fail_completion(record):
            if record["action"] == "folder_restored":
                raise OSError("completion journal unavailable")
            original_log(record)

        with patch.object(app, "append_log", side_effect=fail_completion):
            restored, failures = app.restore_folder(entry, self.root, app.quarantine_root(self.root))
        self.assertTrue(restored.exists())
        self.assertFalse(destination.exists())
        self.assertTrue(any("Folder restored to" in failure for failure in failures))


class FolderBatchTests(FolderFixtures):
    def test_duplicate_scope_is_enforced_again_when_moving(self):
        from dataclasses import replace

        other = self.add_copy_folder("Other imports")
        with self.assertRaisesRegex(ValueError, "outside"):
            folders.plan_folder(self.rows, self.root, self.clean, self.keep, duplicate_root=other)
        invalid = replace(self.plan(), duplicate_root=other)
        with self.assertRaisesRegex(ValueError, "outside"):
            app.quarantine_folder_batch([invalid], allow_empty=True)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_checked_subset_retains_unchecked_copies_and_blocks_unknown_paths(self):
        plan = self.plan()
        checked = plan.matches[0].source
        selected = folders.select_folder_copies([plan], [checked])
        self.assertEqual(len(selected[0].matches), 1)
        self.assertEqual(len(selected[0].remaining_images), 23)
        self.assertFalse(selected[0].whole_folder)
        moved, failures, outcomes = app.quarantine_folder_batch(selected, images_only=True)
        self.assertEqual(moved, [str(checked)])
        self.assertEqual(failures, [])
        self.assertEqual(len(list(self.clean.glob("*.png"))), 23)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertEqual(len(app.fetch_rows(self.root)), 47)
        remaining = folders.remaining_folder_plans([plan], moved)
        self.assertEqual(len(remaining[0].matches), 23)
        self.assertNotIn(checked, remaining[0].files)
        for paths in ([], [self.keep / "original-00.png"], [self.clean / "unknown.png"]):
            with self.assertRaises(ValueError):
                folders.select_folder_copies(remaining, paths)

    def test_image_only_batch_cannot_empty_photo_folder_without_explicit_acknowledgement(self):
        (self.clean / ".DS_Store").write_bytes(b"folder metadata")
        with self.assertRaisesRegex(ValueError, "no images"):
            app.quarantine_folder_batch([self.plan()], images_only=True)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_final_mover_rejects_a_keeper_that_is_also_selected(self):
        plan = self.plan()
        source = plan.matches[0].source
        match = folders.FileMatch(source, source, plan.matches[0].sha256,
                                  folders.identity(source), folders.identity(source))
        expected = {str(source): match}
        with self.assertRaisesRegex(ValueError, "keeper"):
            app.quarantine_selected(expected, self.root, "Folder cleanup", expected=expected)
        self.assertTrue(source.exists())
        self.assertFalse(app.quarantine_root(self.root).exists())
        kept = plan.matches[0].keeper
        reverse = folders.FileMatch(kept, source, match.sha256,
                                    folders.identity(kept), folders.identity(source))
        expected = {str(source): plan.matches[0], str(kept): reverse}
        with self.assertRaisesRegex(ValueError, "keeper"):
            app.quarantine_selected(expected, self.root, "Folder cleanup", expected=expected)
        self.assertTrue(source.exists())
        self.assertTrue(kept.exists())

    def test_mixed_batch_moves_whole_and_partial_folders_and_hashes_shared_keeper_once(self):
        other = self.add_copy_folder("Other imports", sidecar=True)
        with patch.object(folders, "reference_index", wraps=folders.reference_index) as lookup:
            plans = folders.plan_folders(self.rows, self.root, [self.clean, other], self.keep)
        self.assertEqual(lookup.call_count, 1)
        with patch.object(folders, "hash_regular_file", wraps=folders.hash_regular_file) as hashing:
            moved, failures, outcomes = app.quarantine_folder_batch(plans, allow_empty=True)
        self.assertEqual(len(moved), 26)
        self.assertEqual(failures, [])
        self.assertEqual([o["Action"] for o in outcomes], ["Complete folder", "Duplicate images"])
        self.assertFalse(self.clean.exists())
        self.assertEqual(list(other.iterdir()), [other / "notes.txt"])
        self.assertEqual((other / "notes.txt").read_text(), "unique notes")
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertEqual(len(app.fetch_rows(self.root)), 24)
        self.assertEqual(hashing.call_count, 50)  # 26 moved copies + 24 retained files.
        first_keeper = self.keep / "original-00.png"
        self.assertEqual(sum(c.args[0] == first_keeper for c in hashing.call_args_list), 1)

    def test_changed_file_in_last_folder_prevents_entire_batch(self):
        other = self.add_copy_folder("Other imports")
        plans = folders.plan_folders(self.rows, self.root, [self.clean, other], self.keep)
        (other / "copy-1.png").write_bytes(b"changed copy")
        with self.assertRaisesRegex(ValueError, "changed"):
            app.quarantine_folder_batch(plans)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(other.glob("*.png"))), 2)
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_changes_in_earlier_folder_during_later_verification_prevent_moves(self):
        other = self.add_copy_folder("Other imports")
        plans = folders.plan_folders(self.rows, self.root, [self.clean, other], self.keep)

        def change_earlier(i, total):
            if i == total:
                plans[0].matches[0].source.write_bytes(b"changed during batch verification")

        with self.assertRaisesRegex(ValueError, "batch verification"):
            app.quarantine_folder_batch(plans, progress=change_earlier, allow_empty=True)
        self.assertTrue(self.clean.exists())
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_nested_selection_is_counted_and_moved_once(self):
        nested = self.add_copy_folder("Imports/Nested")
        selection = [nested, self.clean, nested]
        self.assertEqual(folders.collapse_folder_selection(selection), [self.clean])
        plans = folders.plan_folders(self.rows, self.root, selection, self.keep)
        moved, failures, outcomes = app.quarantine_folder_batch(plans)
        self.assertEqual(len(moved), 26)
        self.assertEqual(failures, [])
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(self.clean.exists())
        self.assertEqual(len(app.folder_recovery_records(self.root, app.quarantine_root(self.root))), 1)

    def test_invalid_batches_cannot_move_anything(self):
        other = self.add_copy_folder("Other imports")
        first = self.plan()
        different_keeper = folders.plan_folder(self.rows, self.root, other, self.clean)
        nested = self.add_copy_folder("Imports/Nested")
        nested_plan = folders.plan_folder(self.rows, self.root, nested, self.keep)
        for plans in ([], [first, first], [first, different_keeper], [first, nested_plan]):
            with self.subTest(plans=plans):
                with self.assertRaises(ValueError):
                    app.quarantine_folder_batch(plans)
        self.assertTrue(self.clean.exists())
        self.assertTrue(other.exists())
        self.assertFalse(app.quarantine_root(self.root).exists())

    def test_images_only_batch_preserves_complete_directories(self):
        other = self.add_copy_folder("Other imports")
        plans = folders.plan_folders(self.rows, self.root, [self.clean, other], self.keep)
        with patch.object(app, "move_directory", side_effect=AssertionError("Images only")):
            moved, failures, outcomes = app.quarantine_folder_batch(plans, images_only=True, allow_empty=True)
        self.assertEqual(len(moved), 26)
        self.assertEqual(failures, [])
        self.assertEqual(list(self.clean.iterdir()), [])
        self.assertEqual(list(other.iterdir()), [])
        self.assertTrue(all(o["Action"] == "Duplicate images" for o in outcomes))

    def test_later_move_failure_reports_completed_folders_and_preserves_remaining_files(self):
        other = self.add_copy_folder("Other imports", sidecar=True)
        plans = folders.plan_folders(self.rows, self.root, [self.clean, other], self.keep)
        original_move = app.move_to_quarantine

        def fail_later(path, root):
            if folders.within(Path(path), other):
                raise OSError("fixture move unavailable")
            return original_move(path, root)

        with patch.object(app, "move_to_quarantine", side_effect=fail_later):
            moved, failures, outcomes = app.quarantine_folder_batch(plans, allow_empty=True)
        self.assertEqual(len(moved), 24)
        self.assertEqual(len(failures), 2)
        self.assertEqual([o["Images moved"] for o in outcomes], [24, 0])
        self.assertEqual([o["Status"] for o in outcomes], ["Completed", "Check errors"])
        self.assertFalse(self.clean.exists())
        self.assertEqual(len(list(other.glob("*.png"))), 2)
        self.assertEqual(len(app.fetch_rows(self.root)), 26)


class FolderInteractionTests(FolderFixtures):
    def test_image_only_action_cannot_empty_folder_without_separate_acknowledgement(self):
        (self.clean / ".DS_Store").write_bytes(b"folder metadata")
        at = self.app_test()
        self.open_folder_review(at)
        self.assertEqual(next(m for m in at.metric if m.label == "Images staying in source").value, "0")
        next(c for c in at.checkbox if c.label.startswith("I reviewed this folder action:")).check()
        next(b for b in at.button if b.label.startswith("Quarantine all 24")).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertTrue(any("no images" in e.value.casefold() for e in at.error))

    def open_folder_review(self, at, inspect=True):
        at.run()
        at.radio[0].set_value("Folder cleanup").run()
        at.selectbox[0].set_value(self.keep).run()
        if inspect:
            # Selectbox values are FolderSummary objects, not display labels.
            selected = next(s for s in folders.folder_summaries(self.rows, self.root, self.keep)
                            if s.folder == self.clean)
            at.selectbox[-1].set_value(selected).run()
        self.assertEqual(len(at.exception), 0)

    def review_bulk_selection(self, at):
        next(b for b in at.button if b.label == "Review selected folders").click().run()
        next(r for r in at.radio if r.label == "Folder review mode").set_value("Folder actions — all duplicates").run()
        self.assertEqual(len(at.exception), 0)

    def test_whole_folder_action_is_confirmed_and_bounded_to_sample_thumbnails(self):
        at = self.app_test()
        self.open_folder_review(at)
        self.assertEqual(len(at.get("image")), 6)
        self.assertEqual(len(at.multiselect), 0)
        button = next(b for b in at.button if b.label == "Quarantine complete folder")
        self.assertFalse(button.disabled)
        button.click().run()
        self.assertTrue(self.clean.exists())
        self.assertTrue(any("Confirm" in e.value for e in at.error))
        next(c for c in at.checkbox if c.label.startswith("I reviewed this folder action:")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand no images")).check()
        next(b for b in at.button if b.label == "Quarantine complete folder").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(self.clean.exists())
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        at.radio[0].set_value("Quarantine review").run()
        self.assertEqual(len(at.exception), 0)
        at.checkbox[0].check()
        next(b for b in at.button if b.label == "Restore complete folder").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)

    def test_partial_folder_action_keeps_unique_files_and_moves_all_duplicates_at_once(self):
        unique = self.clean / "my-notes.txt"
        unique.write_text("keep this")
        at = self.app_test()
        self.open_folder_review(at)
        self.assertTrue(next(b for b in at.button if b.label == "Quarantine complete folder").disabled)
        next(c for c in at.checkbox if c.label.startswith("I reviewed this folder action:")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand no images")).check()
        next(b for b in at.button if b.label.startswith("Quarantine all 24")).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(list(self.clean.iterdir()), [unique])
        self.assertEqual(unique.read_text(), "keep this")
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)

    def test_overview_lists_all_duplicate_folders_without_inventory_or_previews(self):
        other = self.add_copy_folder("Other imports")
        self.add_copy_folder("Imports/Nested")
        at = self.app_test()
        with patch.object(folders, "inventory", side_effect=AssertionError("List must use index only")):
            self.open_folder_review(at, inspect=False)
            self.assertEqual(len(at.get("image")), 0)
            table = at.dataframe[0].value
            self.assertEqual(set(table["Folder"]), {"Imports", "Imports/Nested", "Other imports"})
            self.assertEqual(table["Duplicate images"].tolist(), [26, 2, 2])
            self.assertTrue(all(table["Kept-copy folders (indexed)"].str.startswith("Originals (")))
            self.assertTrue(next(b for b in at.button if b.label == "Review selected folders").disabled)
            next(c for c in at.checkbox if c.label == "Select all shown folders").check().run()
            self.assertTrue(any("Selected: 2 independent folders, 28" in c.value for c in at.caption))
            self.assertTrue(any("nested selections" in i.value for i in at.info))
            self.assertEqual(len(at.get("image")), 0)
        self.assertTrue(other.exists())

    def test_select_all_batch_requires_confirmation_and_keeps_unique_files(self):
        other = self.add_copy_folder("Other imports", sidecar=True)
        at = self.app_test()
        self.open_folder_review(at, inspect=False)
        next(c for c in at.checkbox if c.label == "Select all shown folders").check().run()
        self.review_bulk_selection(at)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("image")), 0)
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertTrue(self.clean.exists())
        self.assertTrue(any("Confirm" in e.value for e in at.error))
        next(c for c in at.checkbox if c.label.startswith("I reviewed this batch:")).check()
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertTrue(self.clean.exists())
        self.assertTrue(any("no images" in e.value for e in at.error))
        next(c for c in at.checkbox if c.label.startswith("I understand the listed folders")).check()
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(self.clean.exists())
        self.assertEqual(list(other.iterdir()), [other / "notes.txt"])
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        results = at.dataframe[0].value
        self.assertEqual(results["Images moved"].tolist(), [24, 2])
        self.assertTrue(all(results["Status"] == "Completed"))

    def test_checkbox_row_selection_moves_only_selected_folder(self):
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_folder_review(at, inspect=False)
        table = at.dataframe[0].value
        position = table.index[table["Folder"] == "Other imports"][0]
        editor_key = next(k for k in at.session_state if k.startswith("folder_table_"))
        at.session_state[editor_key] = {"edited_rows": {int(position): {"Select": True}},
                                        "added_rows": [], "deleted_rows": []}
        at.run()
        self.assertTrue(any("Selected: 1 independent folders, 2" in c.value for c in at.caption))
        self.review_bulk_selection(at)
        next(c for c in at.checkbox if c.label.startswith("I reviewed this batch:")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand the listed folders")).check()
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(other.exists())
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)

    def test_changing_batch_action_resets_confirmation(self):
        at = self.app_test()
        self.open_folder_review(at, inspect=False)
        next(c for c in at.checkbox if c.label == "Select all shown folders").check().run()
        self.review_bulk_selection(at)
        next(c for c in at.checkbox if c.label.startswith("I reviewed this batch:")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand the listed folders")).check().run()
        next(s for s in at.selectbox if s.label == "Batch action").set_value("Duplicate images only").run()
        self.assertFalse(next(c for c in at.checkbox if c.label.startswith("I reviewed this batch:")).value)
        self.assertFalse(next(c for c in at.checkbox if c.label.startswith("I understand the listed folders")).value)
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertTrue(self.clean.exists())
        self.assertTrue(any("Confirm" in e.value for e in at.error))

    def test_filter_and_coverage_limit_select_all_to_shown_folders(self):
        other = self.add_copy_folder("Other imports")
        unique = self.clean / "unique.png"
        Image.new("RGB", (32, 32), "white").save(unique)
        metadata = unique.stat()
        row = (str(unique), metadata.st_size, metadata.st_mtime,
               app.file_sha256(unique), "unique-pixel", 32, 32, "eeeeeeeeeeeeeeee", None)
        conn = app.connect_db()
        conn.execute("INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?)", (*row, 0))
        conn.commit()
        conn.close()
        at = self.app_test()
        self.open_folder_review(at, inspect=False)
        next(c for c in at.checkbox if c.label.startswith("Only folders where every")).check().run()
        self.assertEqual(at.dataframe[0].value["Folder"].tolist(), ["Other imports"])
        next(c for c in at.checkbox if c.label == "Select all shown folders").check().run()
        self.assertTrue(any("Selected: 1 independent folders, 2" in c.value for c in at.caption))
        next(t for t in at.text_input if t.label == "Filter folder paths").set_value("Imports/").run()
        self.assertEqual(len(at.dataframe), 0)
        self.assertFalse(any(b.label == "Quarantine selected folders" for b in at.button))
        self.assertTrue(other.exists())
        self.assertTrue(unique.exists())


class FolderScopeTests(FolderFixtures):
    def open_scope(self, at):
        at.run()
        at.radio[0].set_value("Folder cleanup").run()
        self.assertTrue(next(s for s in at.selectbox if s.label == "Find duplicates in (optional)").disabled)
        next(s for s in at.selectbox if s.label == "Original folder (protected)").set_value(self.keep).run()
        self.assertEqual(len(at.exception), 0)

    def duplicate_selector(self, at):
        return next(s for s in at.selectbox if s.label == "Find duplicates in (optional)")

    def test_two_selectors_exclude_original_tree_and_blank_lists_other_folders(self):
        self.add_copy_folder("Originals/Nested", count=1)
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_scope(at)
        selector = self.duplicate_selector(at)
        self.assertIsNone(selector.value)
        self.assertFalse(selector.disabled)
        self.assertNotIn("Originals", selector.options)
        self.assertNotIn("Originals/Nested", selector.options)
        self.assertEqual(set(at.dataframe[0].value["Folder"]), {"Imports", "Other imports"})
        selector.set_value(other).run()
        self.assertEqual(len(at.get("image")), 4)
        self.assertFalse(any(b.label == "Review selected folders" for b in at.button))
        self.duplicate_selector(at).set_value(None).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("image")), 0)
        self.assertEqual(set(at.dataframe[0].value["Folder"]), {"Imports", "Other imports"})

    def test_focused_comparison_moves_only_copies_in_second_folder(self):
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_scope(at)
        self.duplicate_selector(at).set_value(other).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("image")), 4)
        boxes = [c for c in at.checkbox if c.label.startswith("Quarantine copy:")]
        self.assertEqual(len(boxes), 2)
        self.assertTrue(all("Other imports/" in c.label for c in boxes))
        boxes[0].check().run()
        next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).check()
        next(b for b in at.button if b.label == "Quarantine checked images").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(other.glob("*.png"))), 1)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertEqual(self.duplicate_selector(at).value, other)
        self.assertEqual(len(at.get("image")), 2)

    def test_changing_second_folder_resets_choices_and_confirmation(self):
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_scope(at)
        self.duplicate_selector(at).set_value(self.clean).run()
        next(c for c in at.checkbox if c.label.startswith("Quarantine copy:")).check().run()
        next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).check().run()
        self.duplicate_selector(at).set_value(other).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(all(not c.value for c in at.checkbox if c.label.startswith("Quarantine copy:")))
        self.assertFalse(next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).value)
        self.assertTrue(next(b for b in at.button if b.label == "Quarantine checked images").disabled)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(other.glob("*.png"))), 2)

    def test_emptied_scope_does_not_silently_expand_to_other_folders(self):
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_scope(at)
        self.duplicate_selector(at).set_value(other).run()
        next(b for b in at.button if b.label == "Select all copies on this page").click().run()
        next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand the checked copies")).check()
        next(b for b in at.button if b.label == "Quarantine checked images").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(self.duplicate_selector(at).value, other)
        self.assertEqual(len(list(other.iterdir())), 0)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(at.get("image")), 0)
        self.assertTrue(any("selected duplicate folder" in i.value for i in at.info))

    def test_changing_original_resets_scope_and_protects_new_original(self):
        at = self.app_test()
        self.open_scope(at)
        self.duplicate_selector(at).set_value(self.clean).run()
        next(c for c in at.checkbox if c.label.startswith("Quarantine copy:")).check().run()
        next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).check().run()
        next(s for s in at.selectbox if s.label == "Original folder (protected)").set_value(self.clean).run()
        self.assertEqual(len(at.exception), 0)
        self.assertIsNone(self.duplicate_selector(at).value)
        self.assertNotIn("Imports", self.duplicate_selector(at).options)
        self.assertEqual(len(at.get("image")), 0)
        self.duplicate_selector(at).set_value(self.keep).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(all(not c.value for c in at.checkbox if c.label.startswith("Quarantine copy:")))
        self.assertFalse(next(c for c in at.checkbox if c.label.startswith("I reviewed the ")).value)
        self.assertTrue(next(b for b in at.button if b.label == "Quarantine checked images").disabled)
        self.assertTrue(all("Originals/" in c.label for c in at.checkbox if c.label.startswith("Quarantine copy:")))
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)

    def test_removed_scope_remains_explicit_after_complete_folder_action(self):
        other = self.add_copy_folder("Other imports")
        at = self.app_test()
        self.open_scope(at)
        self.duplicate_selector(at).set_value(other).run()
        next(r for r in at.radio if r.label == "Folder review mode").set_value("Folder actions — all duplicates").run()
        next(c for c in at.checkbox if c.label.startswith("I reviewed this batch:")).check()
        next(c for c in at.checkbox if c.label.startswith("I understand the listed folders")).check()
        next(b for b in at.button if b.label == "Quarantine selected folders").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(other.exists())
        self.assertEqual(self.duplicate_selector(at).value, other)
        self.assertTrue(any("no longer present" in i.value for i in at.info))
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)


class FolderThumbnailTests(FolderFixtures):
    def open_thumbnails(self, at, folder=None):
        folder = folder or self.clean
        at.run()
        at.radio[0].set_value("Folder cleanup").run()
        at.selectbox[0].set_value(self.keep).run()
        table = at.dataframe[0].value
        position = int(table.index[table["Folder"] == str(folder.relative_to(self.root))][0])
        editor_key = next(k for k in at.session_state if k.startswith("folder_table_"))
        at.session_state[editor_key] = {"edited_rows": {position: {"Select": True}},
                                      "added_rows": [], "deleted_rows": []}
        at.run()
        next(b for b in at.button if b.label == "Review selected folders").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(next(r for r in at.radio if r.label == "Folder review mode").value,
                         "Thumbnails — choose copies")

    def checked_boxes(self, at):
        return [c for c in at.checkbox if c.label.startswith("Quarantine copy:")]

    def confirmation(self, at):
        return next(c for c in at.checkbox if c.label.startswith("I reviewed the "))

    def move_button(self, at):
        return next(b for b in at.button if b.label == "Quarantine checked images")

    def test_default_pairs_move_only_checked_copy_and_continue_without_reselecting_folder(self):
        at = self.app_test()
        self.open_thumbnails(at)
        self.assertEqual(len(at.get("image")), 12)
        self.assertEqual(len(self.checked_boxes(at)), 6)
        self.assertTrue(self.move_button(at).disabled)
        source = self.clean / "renamed-copy-00.png"
        self.checked_boxes(at)[0].check().run()
        self.assertTrue(self.confirmation(at).label.startswith("I reviewed the 1 checked"))
        self.move_button(at).click().run()
        self.assertTrue(source.exists())
        self.assertTrue(any("Confirm" in e.value for e in at.error))
        self.confirmation(at).check()
        self.move_button(at).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(source.exists())
        self.assertEqual(len(list(self.clean.glob("*.png"))), 23)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        self.assertEqual(len(at.get("image")), 12)
        self.assertTrue(all(not c.value for c in self.checked_boxes(at)))
        self.assertEqual(json.loads(app.DECISIONS_PATH.read_text())[0]["from"], str(source))
        # A second rerun must retain the resumed folder and review, not drop it.
        self.checked_boxes(at)[0].check().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("image")), 12)
        self.assertTrue(self.confirmation(at).label.startswith("I reviewed the 1 checked"))

    def test_choices_persist_across_pages_and_one_action_moves_both(self):
        at = self.app_test()
        self.open_thumbnails(at)
        self.checked_boxes(at)[0].check().run()
        next(n for n in at.number_input if n.label == "Thumbnail page").set_value(2).run()
        self.assertEqual(len(at.get("image")), 12)
        self.checked_boxes(at)[0].check().run()
        self.assertTrue(self.confirmation(at).label.startswith("I reviewed the 2 checked"))
        next(n for n in at.number_input if n.label == "Thumbnail page").set_value(1).run()
        self.assertTrue(self.checked_boxes(at)[0].value)
        self.confirmation(at).check()
        self.move_button(at).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 22)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)
        records = json.loads(app.DECISIONS_PATH.read_text())
        self.assertEqual({Path(e["from"]).name for e in records},
                         {"renamed-copy-00.png", "renamed-copy-06.png"})

    def test_two_image_folder_requires_zero_image_acknowledgement(self):
        other = self.add_copy_folder("Other imports", sidecar=True)
        at = self.app_test()
        self.open_thumbnails(at, other)
        self.assertEqual(len(at.get("image")), 4)
        next(b for b in at.button if b.label == "Select all copies on this page").click().run()
        self.assertTrue(all(c.value for c in self.checked_boxes(at)))
        self.confirmation(at).check()
        self.move_button(at).click().run()
        self.assertEqual(len(list(other.glob("*.png"))), 2)
        self.assertTrue(any("no images" in e.value for e in at.error))
        next(c for c in at.checkbox if c.label.startswith("I understand the checked copies")).check()
        self.move_button(at).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(list(other.iterdir()), [other / "notes.txt"])
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertEqual(len(list(self.keep.glob("*.png"))), 24)

    def test_clear_page_resets_choices_and_confirmation(self):
        at = self.app_test()
        self.open_thumbnails(at)
        next(b for b in at.button if b.label == "Select all copies on this page").click().run()
        self.assertTrue(self.confirmation(at).label.startswith("I reviewed the 6 checked"))
        self.confirmation(at).check().run()
        next(b for b in at.button if b.label == "Clear this page").click().run()
        self.assertTrue(all(not c.value for c in self.checked_boxes(at)))
        self.assertFalse(self.confirmation(at).value)
        self.assertTrue(self.move_button(at).disabled)

    def test_changed_protected_match_blocks_checked_copy(self):
        at = self.app_test()
        self.open_thumbnails(at)
        self.checked_boxes(at)[0].check().run()
        (self.keep / "original-00.png").write_bytes(b"changed protected copy")
        self.confirmation(at).check()
        self.move_button(at).click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.clean.glob("*.png"))), 24)
        self.assertFalse(app.quarantine_root(self.root).exists())
        self.assertTrue(any("changed" in e.value for e in at.error))


if __name__ == "__main__":
    unittest.main()
