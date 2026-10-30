use dedupe_core::hash::sha256_file;
use dedupe_index::{op_journal, Connection, IndexError};
use std::path::Path;
use tracing::{info, warn};

/// Resolve PENDING journal entries left over from a previous crashed run.
/// Returns a list of alert messages for entries that need manual review.
pub fn reconcile_pending(conn: &Connection) -> Result<Vec<String>, IndexError> {
    let pending = op_journal::get_pending(conn)?;
    let mut alerts = Vec::new();

    for entry in pending {
        let src_exists = Path::new(&entry.source_path).exists();
        let dst_exists = entry
            .dest_path
            .as_deref()
            .map(|d| Path::new(d).exists())
            .unwrap_or(false);

        match (src_exists, dst_exists) {
            (true, false) => {
                op_journal::mark_rolled_back(conn, entry.id)?;
                info!(
                    "reconcile: {} → ROLLED_BACK (source preserved, move never completed)",
                    entry.source_path
                );
            }
            (false, true) => {
                op_journal::mark_completed(conn, entry.id)?;
                info!(
                    "reconcile: {} → COMPLETED (move completed, journal not updated)",
                    entry.source_path
                );
            }
            (true, true) => {
                if let Some(dest) = &entry.dest_path {
                    let dest_hash = sha256_file(Path::new(dest)).ok();
                    let hashes_match = dest_hash
                        .as_ref()
                        .map(|h| h.as_ref() == entry.sha256.as_slice())
                        .unwrap_or(false);
                    if hashes_match {
                        let _ = std::fs::remove_file(&entry.source_path);
                        op_journal::mark_completed(conn, entry.id)?;
                        info!(
                            "reconcile: {} → COMPLETED (dest verified, source removed)",
                            entry.source_path
                        );
                    } else {
                        warn!(
                            "reconcile: {} — both source and dest exist but hashes differ",
                            entry.source_path
                        );
                        alerts.push(format!(
                            "Manual review required: '{}' and '{}' both exist but differ. \
                             Check both files before deleting either.",
                            entry.source_path,
                            dest
                        ));
                    }
                }
            }
            (false, false) => {
                op_journal::mark_failed(conn, entry.id)?;
                warn!(
                    "reconcile: {} → FAILED (both source and dest missing)",
                    entry.source_path
                );
            }
        }
    }

    Ok(alerts)
}

#[cfg(test)]
mod tests {
    use super::*;
    use dedupe_index::db;
    use tempfile::tempdir;

    #[test]
    fn no_pending_entries_returns_empty_alerts() {
        let dir = tempdir().unwrap();
        let conn = db::open(&dir.path().join("test.db")).unwrap();
        let alerts = reconcile_pending(&conn).unwrap();
        assert!(alerts.is_empty());
    }

    #[test]
    fn pending_with_missing_both_marks_failed() {
        let dir = tempdir().unwrap();
        let conn = db::open(&dir.path().join("test.db")).unwrap();
        let id = op_journal::write_pending(
            &conn,
            "/nonexistent/src.jpg",
            "/nonexistent/dst.jpg",
            &[0u8; 32],
            "/nonexistent/keep.jpg",
            false,
        )
        .unwrap();

        let alerts = reconcile_pending(&conn).unwrap();
        assert!(alerts.is_empty());

        let pending = op_journal::get_pending(&conn).unwrap();
        assert!(pending.is_empty(), "FAILED entries should not appear in pending");
        let _ = id;
    }

    #[test]
    fn pending_with_only_source_marks_rolled_back() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("src.jpg");
        std::fs::write(&src, b"data").unwrap();

        let conn = db::open(&dir.path().join("test.db")).unwrap();
        op_journal::write_pending(
            &conn,
            src.to_str().unwrap(),
            "/nonexistent/dst.jpg",
            &[0u8; 32],
            "/nonexistent/keep.jpg",
            false,
        )
        .unwrap();

        let alerts = reconcile_pending(&conn).unwrap();
        assert!(alerts.is_empty());
        let pending = op_journal::get_pending(&conn).unwrap();
        assert!(pending.is_empty());
        assert!(src.exists(), "source should be preserved after ROLLED_BACK");
    }
}
