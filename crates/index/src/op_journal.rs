use rusqlite::Connection;
use crate::error::{IndexError, promote};

#[derive(Debug)]
pub struct JournalEntry {
    pub id: i64,
    pub source_path: String,
    pub dest_path: Option<String>,
    pub sha256: Vec<u8>,
    pub status: String,
    pub cross_volume: bool,
}

pub fn write_pending(
    conn: &Connection,
    source: &str,
    dest: &str,
    sha256: &[u8],
    keeper: &str,
    cross_volume: bool,
) -> Result<i64, IndexError> {
    conn.execute(
        r#"INSERT INTO op_journal (operation, status, source_path, dest_path, sha256, keeper_path, cross_volume)
           VALUES ('quarantine', 'PENDING', ?1, ?2, ?3, ?4, ?5)"#,
        rusqlite::params![source, dest, sha256, keeper, cross_volume as i64],
    )
    .map_err(promote)?;
    Ok(conn.last_insert_rowid())
}

pub fn mark_completed(conn: &Connection, id: i64) -> Result<(), IndexError> {
    conn.execute(
        r#"UPDATE op_journal SET status='COMPLETED', completed_at=datetime('now') WHERE id=?1"#,
        [id],
    )
    .map_err(promote)?;
    Ok(())
}

pub fn mark_failed(conn: &Connection, id: i64) -> Result<(), IndexError> {
    conn.execute(
        r#"UPDATE op_journal SET status='FAILED', completed_at=datetime('now') WHERE id=?1"#,
        [id],
    )
    .map_err(promote)?;
    Ok(())
}

pub fn mark_rolled_back(conn: &Connection, id: i64) -> Result<(), IndexError> {
    conn.execute(
        r#"UPDATE op_journal SET status='ROLLED_BACK', completed_at=datetime('now') WHERE id=?1"#,
        [id],
    )
    .map_err(promote)?;
    Ok(())
}

pub fn mark_deleted(conn: &Connection, id: i64) -> Result<(), IndexError> {
    conn.execute(
        r#"UPDATE op_journal SET status='DELETED', completed_at=datetime('now') WHERE id=?1"#,
        [id],
    )
    .map_err(promote)?;
    Ok(())
}

pub struct CompletedEntry {
    pub id: i64,
    pub source_path: String,
    pub dest_path: String,
    pub bytes_moved: u64,
    pub completed_at: String,
}

pub fn list_quarantined(conn: &Connection) -> Result<Vec<CompletedEntry>, IndexError> {
    let mut stmt = conn
        .prepare(
            r#"SELECT id, source_path, dest_path, completed_at
               FROM op_journal
               WHERE operation='quarantine' AND status='COMPLETED'
               ORDER BY completed_at DESC"#,
        )
        .map_err(promote)?;

    let rows = stmt
        .query_map([], |row| {
            Ok(CompletedEntry {
                id: row.get(0)?,
                source_path: row.get(1)?,
                dest_path: row.get(2)?,
                bytes_moved: 0,
                completed_at: row.get::<_, Option<String>>(3)?.unwrap_or_default(),
            })
        })
        .map_err(promote)?;

    rows.collect::<Result<Vec<_>, _>>().map_err(IndexError::Sqlite)
}

pub fn get_pending(conn: &Connection) -> Result<Vec<JournalEntry>, IndexError> {
    let mut stmt = conn
        .prepare(
            r#"SELECT id, source_path, dest_path, sha256, status, cross_volume
               FROM op_journal WHERE status='PENDING'"#,
        )
        .map_err(promote)?;

    let rows = stmt
        .query_map([], |row| {
            Ok(JournalEntry {
                id: row.get(0)?,
                source_path: row.get(1)?,
                dest_path: row.get(2)?,
                sha256: row.get(3)?,
                status: row.get(4)?,
                cross_volume: row.get::<_, i64>(5)? != 0,
            })
        })
        .map_err(promote)?;

    rows.collect::<Result<Vec<_>, _>>().map_err(IndexError::Sqlite)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db;
    use tempfile::tempdir;

    fn open_test_db() -> (tempfile::TempDir, Connection) {
        let dir = tempdir().unwrap();
        let conn = db::open(&dir.path().join("test.db")).unwrap();
        (dir, conn)
    }

    #[test]
    fn write_and_read_pending() {
        let (_dir, conn) = open_test_db();
        let id = write_pending(&conn, "/src/a.jpg", "/q/a.jpg", &[0u8; 32], "/src/keep.jpg", false).unwrap();
        assert!(id > 0);
        let entries = get_pending(&conn).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].source_path, "/src/a.jpg");
        assert_eq!(entries[0].status, "PENDING");
    }

    #[test]
    fn mark_completed_clears_from_pending() {
        let (_dir, conn) = open_test_db();
        let id = write_pending(&conn, "/src/b.jpg", "/q/b.jpg", &[1u8; 32], "/src/keep.jpg", false).unwrap();
        mark_completed(&conn, id).unwrap();
        let pending = get_pending(&conn).unwrap();
        assert!(pending.is_empty());
    }

    #[test]
    fn mark_rolled_back_clears_from_pending() {
        let (_dir, conn) = open_test_db();
        let id = write_pending(&conn, "/src/c.jpg", "/q/c.jpg", &[2u8; 32], "/src/keep.jpg", false).unwrap();
        mark_rolled_back(&conn, id).unwrap();
        let pending = get_pending(&conn).unwrap();
        assert!(pending.is_empty());
    }
}
