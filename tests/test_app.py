import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

import app


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class ReviewInteractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dedupe-review-test-")
        self.addCleanup(self.temp.cleanup)
        self.app_dir = Path(self.temp.name).resolve()
        self.root = self.app_dir / "images"
        self.root.mkdir()
        conn = sqlite3.connect(self.app_dir / "dedupe_cache.sqlite3")
        conn.execute("""CREATE TABLE images (
            path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime REAL NOT NULL,
            sha256 TEXT, pixel_hash TEXT, width INTEGER, height INTEGER,
            phash TEXT, error TEXT, scanned_at REAL NOT NULL
        )""")
        for group in range(12):
            for copy in range(2):
                path = self.root / f"group-{group:02d}-copy-{copy}.png"
                Image.new("RGB", (16, 16), (group * 20, 0, 0)).save(path)
                stat = path.stat()
                conn.execute("INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?)", (
                    str(path), stat.st_size, stat.st_mtime, f"sha-{group}",
                    f"pixels-{group}", 16, 16, f"{group:016x}", None, 0,
                ))
        conn.commit()
        conn.close()
        source = APP_PATH.read_text().replace(
            "APP_DIR = Path(__file__).resolve().parent",
            f"APP_DIR = Path({str(self.app_dir)!r})",
        ).replace('str(Path.home() / "Pictures")', repr(str(self.root)))
        self.at = AppTest.from_string(source, default_timeout=15)

    def test_review_only_renders_one_bounded_page(self):
        self.at.run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertGreater(len(self.at.multiselect), 0)
        self.assertLessEqual(len(self.at.multiselect), 5)
        self.assertEqual(len(self.at.get("image")), 10)
        self.assertEqual(len(self.at.get("form")), 1)

    def move_button(self):
        return next(b for b in self.at.button if b.label == "Move selected copies to quarantine")

    def test_confirmation_is_required_and_no_files_move_without_it(self):
        self.at.run()
        self.move_button().click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(list(self.root.glob("*.png"))), 24)
        self.assertTrue(any("Confirm" in e.value for e in self.at.error))

    def test_changed_metadata_resets_old_review_confirmation(self):
        self.at.run()
        old_snapshot = self.at.session_state["review_snapshot"]
        self.at.checkbox[0].check().run()
        conn = sqlite3.connect(self.app_dir / "dedupe_cache.sqlite3")
        conn.execute("UPDATE images SET width = width + 1 WHERE path = ?",
                     (str(self.root / "group-00-copy-0.png"),))
        conn.commit()
        conn.close()
        self.at.run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertIsNot(self.at.session_state["review_snapshot"], old_snapshot)
        self.assertFalse(self.at.checkbox[0].value)

    def test_page_move_preserves_keepers_and_advances_to_next_groups(self):
        self.at.run()
        selected = {p for widget in self.at.multiselect for p in widget.value}
        keepers = {str(self.root / f"group-{i:02d}-copy-0.png") for i in range(5)}
        self.at.checkbox[0].check()
        self.move_button().click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(list(self.root.glob("*.png"))), 19)
        self.assertEqual(len(list(self.root.parent.glob("images_Duplicate_Quarantine/*.png"))), 5)
        self.assertTrue(all(not Path(p).exists() for p in selected))
        self.assertTrue(all(Path(p).exists() for p in keepers))
        self.assertEqual(len(self.at.get("image")), 10)
        self.assertFalse(self.at.checkbox[0].value)
        self.assertTrue(all(p not in selected for w in self.at.multiselect for p in w.value))
        history = json.loads((self.app_dir / "review_decisions.json").read_text())
        self.assertEqual(len(history), 5)

    def test_cannot_move_every_copy(self):
        self.at.run()
        self.at.multiselect[0].set_value([str(p) for p in sorted(self.root.glob("group-00-*.png"))])
        self.at.checkbox[0].check()
        self.move_button().click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(list(self.root.glob("*.png"))), 24)
        self.assertTrue(any("Keep at least one" in e.value for e in self.at.error))

    def test_missing_keeper_blocks_move_of_last_available_copy(self):
        self.at.run()
        # Simulate an external move after review loaded; no actual fixture deletion.
        keeper = self.root / "group-00-copy-0.png"
        keeper.rename(self.app_dir / "temporarily-moved-keeper.png")
        self.at.checkbox[0].check()
        self.move_button().click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertTrue((self.root / "group-00-copy-1.png").exists())
        self.assertFalse((self.root.parent / "images_Duplicate_Quarantine").exists())
        self.assertTrue(any("keeper is missing" in e.value for e in self.at.error))

    def test_visual_groups_are_reused_after_selection_and_affected_move(self):
        self.at.run()
        self.at.radio[0].set_value("Visually similar").run()
        self.assertEqual(len(self.at.exception), 0)
        snapshot = self.at.session_state["review_snapshot"]
        original_groups = snapshot.groups[("visual", 6)]
        self.at.run()
        self.assertIs(self.at.session_state["review_snapshot"], snapshot)
        self.assertIs(snapshot.groups[("visual", 6)], original_groups)
        self.assertEqual(len(self.at.get("image")), 6)
        # Retain more than one file so regrouping of the affected component is tested.
        chosen = [str(p) for p in sorted(self.root.glob("group-00-*.png"))]
        self.at.multiselect[0].set_value(chosen)
        self.at.checkbox[0].check()
        self.move_button().click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertIs(self.at.session_state["review_snapshot"], snapshot)
        self.assertEqual(len(snapshot.rows), 22)
        self.assertEqual(len(self.at.get("image")), 6)

    def test_quarantine_does_not_render_duplicate_groups_and_restore_avoids_collision(self):
        self.at.run()
        self.at.checkbox[0].check()
        self.move_button().click().run()
        history = json.loads((self.app_dir / "review_decisions.json").read_text())
        original = Path(history[0]["from"])
        original.write_bytes(b"existing occupant")
        self.at.radio[0].set_value("Quarantine review").run()
        self.assertEqual(len(self.at.multiselect), 0)
        self.assertEqual(len(self.at.get("image")), 1)
        selected = Path(self.at.selectbox[0].value)
        self.at.checkbox[0].check()
        next(b for b in self.at.button if b.label == "Restore selected file").click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertFalse(selected.exists())
        self.assertEqual(original.read_bytes(), b"existing occupant")
        history = json.loads((self.app_dir / "review_decisions.json").read_text())
        self.assertEqual(history[-1]["action"], "restored")
        self.assertTrue(Path(history[-1]["to"]).exists())
        self.assertNotEqual(history[-1]["to"], str(original))

    def test_delete_confirmation_does_not_follow_changed_quarantine_selection(self):
        self.at.run()
        self.at.checkbox[0].check()
        self.move_button().click().run()
        self.at.radio[0].set_value("Quarantine review").run()
        first = Path(self.at.selectbox[0].value)
        self.at.checkbox[1].check().run()
        other = next(p for p in sorted(first.parent.glob("*.png")) if p != first)
        self.at.selectbox[0].set_value(str(other)).run()
        self.assertFalse(self.at.checkbox[1].value)
        next(b for b in self.at.button if b.label == "Permanently delete selected file").click().run()
        self.assertTrue(other.exists())
        self.assertTrue(first.exists())
        self.at.checkbox[1].check()
        next(b for b in self.at.button if b.label == "Permanently delete selected file").click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertFalse(other.exists())
        self.assertTrue(first.exists())


def make_row(path, value, sha="same", pixel="same"):
    return (path, 100, 0, sha, pixel, 10, 10, f"{value:016x}", None)


def canonical(groups):
    return sorted(sorted(row[0] for row in group) for group in groups)


def brute_force_groups(rows, radius):
    valid = [row for row in rows if row[7] and not row[8]]
    components = [{i} for i in range(len(valid))]
    for i in range(len(valid)):
        for j in range(i):
            if (int(valid[i][7], 16) ^ int(valid[j][7], 16)).bit_count() <= radius:
                a = next(c for c in components if i in c)
                b = next(c for c in components if j in c)
                if a is not b:
                    a.update(b)
                    components.remove(b)
    return [[valid[i] for i in sorted(c)] for c in components if len(c) > 1]


class GroupingTests(unittest.TestCase):
    def test_optimized_grouping_matches_independent_connected_components(self):
        rng = random.Random(27)
        values = [rng.getrandbits(16) for _ in range(80)]
        values += values[:20] + [0, 1, 3, 7, 15, 31, 63]
        rows = [make_row(str(i), value) for i, value in enumerate(values)]
        rows += [("invalid", 0, 0, None, None, None, None, None, "decode error")]
        for radius in (0, 1, 2, 6, 16):
            with self.subTest(radius=radius):
                self.assertEqual(canonical(app.perceptual_groups(rows, radius)),
                                 canonical(brute_force_groups(rows, radius)))

    def test_removing_bridge_splits_visual_group_without_rebuilding_unaffected_groups(self):
        rows = [make_row(name, value) for name, value in
                (("a", 0), ("bridge", 1), ("c", 3), ("d", 7),
                 ("other-a", 0xffff), ("other-b", 0xfffe))]
        snapshot = app.ReviewSnapshot("test", rows, None)
        for category in ("byte", "pixel", "visual"):
            snapshot.get_groups(category, 1)
        unchanged = snapshot.groups[("visual", 1)][1]
        with patch.object(app, "perceptual_groups", wraps=app.perceptual_groups) as regroup:
            snapshot.remove_paths(["bridge"])
            self.assertEqual(regroup.call_count, 1)
            self.assertEqual({r[0] for r in regroup.call_args.args[0]}, {"a", "c", "d"})
        self.assertIs(snapshot.groups[("visual", 1)][1], unchanged)
        self.assertEqual(canonical(snapshot.get_groups("visual", 1)),
                         canonical(brute_force_groups(snapshot.rows, 1)))
        for category, column in (("byte", 3), ("pixel", 4)):
            self.assertEqual(canonical(snapshot.get_groups(category, 1)),
                             canonical(app.grouped(snapshot.rows, column)))


class BatchMoveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dedupe-batch-test-")
        self.addCleanup(self.temp.cleanup)
        self.app_dir = Path(self.temp.name).resolve()
        self.root = self.app_dir / "images_with_underscores"
        self.root.mkdir()
        for name in ("APP_DIR", "DB_PATH", "DECISIONS_PATH"):
            value = {"APP_DIR": self.app_dir, "DB_PATH": self.app_dir / "index.sqlite3",
                     "DECISIONS_PATH": self.app_dir / "history.json"}[name]
            self.enterContext(patch.object(app, name, value))
        self.paths = []
        conn = app.connect_db()
        for i in range(3):
            path = self.root / f"copy-{i}.png"
            Image.new("RGB", (16, 16), "red").save(path)
            self.paths.append(path)
            conn.execute("INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (*make_row(str(path), 0), 0))
        conn.commit()
        conn.close()

    def test_batch_uses_one_connection_and_history_write_and_preserves_collision(self):
        destination = app.quarantine_root(self.root) / self.paths[0].name
        destination.parent.mkdir()
        destination.write_bytes(b"existing quarantined file")
        with patch.object(app, "connect_db", wraps=app.connect_db) as connect, \
             patch.object(app, "append_logs", wraps=app.append_logs) as history:
            moved, failures = app.quarantine_selected([str(p) for p in self.paths[:2]], self.root, "byte")
            self.assertEqual(connect.call_count, 1)
            self.assertEqual(history.call_count, 1)
        self.assertEqual(failures, [])
        self.assertEqual(len(moved), 2)
        self.assertEqual(destination.read_bytes(), b"existing quarantined file")
        self.assertEqual(len(app.fetch_rows(self.root)), 1)
        self.assertEqual(len(json.loads(app.DECISIONS_PATH.read_text())), 2)
        self.assertTrue(self.paths[2].exists())

    def test_partial_move_failure_is_reported_and_successful_move_is_recorded(self):
        outside = self.app_dir / "outside.png"
        outside.write_bytes(b"outside source")
        selected = [str(self.paths[0]), str(self.root / "missing.png"), str(outside)]
        moved, failures = app.quarantine_selected(selected, self.root, "byte")
        self.assertEqual(len(moved), 1)
        self.assertEqual(len(failures), 2)
        self.assertTrue(outside.exists())
        self.assertTrue(self.paths[1].exists())
        self.assertEqual(len(app.fetch_rows(self.root)), 2)
        self.assertEqual(len(json.loads(app.DECISIONS_PATH.read_text())), 1)

    def test_corrupt_history_is_preserved_and_failure_is_visible(self):
        app.DECISIONS_PATH.write_text("invalid history")
        moved, failures = app.quarantine_selected([str(self.paths[0])], self.root, "byte")
        self.assertEqual(len(moved), 1)
        self.assertTrue(any("history could not be saved" in error for error in failures))
        self.assertEqual(app.DECISIONS_PATH.read_text(), "invalid history")
        self.assertTrue(Path(moved[0]["to"]).exists())

    def test_thumbnail_cache_reuses_decodes_and_invalidates_changed_file(self):
        path = self.paths[0]
        app.cached_thumb.clear()
        with patch.object(app.Image, "open", wraps=app.Image.open) as decode:
            first = app.thumb(path)
            self.assertEqual(app.thumb(path), first)
            self.assertEqual(decode.call_count, 1)
            Image.new("RGB", (32, 32), "blue").save(path)
            self.assertNotEqual(app.thumb(path), first)
            self.assertEqual(decode.call_count, 2)


if __name__ == "__main__":
    unittest.main()
