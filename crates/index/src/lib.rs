pub mod db;
pub mod error;
pub mod file_cache;
pub mod migrations;

pub use error::IndexError;
pub use rusqlite;
pub use rusqlite::Connection;

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn opens_and_migrates() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("test.db");
        let conn = db::open(&db_path).unwrap();
        let v: String = conn
            .query_row(
                "SELECT value FROM scan_metadata WHERE key = ?1",
                ["schema_version"],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(v, "1");
    }

    #[test]
    fn wal_mode_is_active() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("wal.db");
        let conn = db::open(&db_path).unwrap();
        let mode: String = conn
            .query_row("PRAGMA journal_mode", [], |r| r.get(0))
            .unwrap();
        assert_eq!(mode, "wal");
    }

    #[test]
    fn all_three_tables_exist() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("tables.db");
        let conn = db::open(&db_path).unwrap();
        for table in &["file_cache", "op_journal", "scan_metadata"] {
            let count: i64 = conn
                .query_row(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?1",
                    [table],
                    |r| r.get(0),
                )
                .unwrap();
            assert_eq!(count, 1, "table {table} missing");
        }
    }
}
