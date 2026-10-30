use rusqlite::Connection;
use crate::error::IndexError;

pub fn run(conn: &Connection) -> Result<(), IndexError> {
    let version = get_version(conn).unwrap_or(0);
    if version < 1 {
        migrate_to_v1(conn)?;
    }
    Ok(())
}

fn get_version(conn: &Connection) -> Option<u32> {
    conn.query_row(
        "SELECT value FROM scan_metadata WHERE key = ?1",
        ["schema_version"],
        |row| row.get::<_, String>(0),
    )
    .ok()?
    .parse()
    .ok()
}

fn migrate_to_v1(conn: &Connection) -> Result<(), IndexError> {
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS file_cache (
            id             INTEGER PRIMARY KEY,
            path           TEXT NOT NULL UNIQUE,
            size           INTEGER NOT NULL,
            mtime_ns       INTEGER NOT NULL,
            analyzer_version INTEGER NOT NULL DEFAULT 1,
            sha256         BLOB,
            pixel_hash     BLOB,
            error          TEXT,
            scanned_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS op_journal (
            id             INTEGER PRIMARY KEY,
            operation      TEXT NOT NULL CHECK(operation IN ('quarantine','restore','delete')),
            status         TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETED','FAILED','ROLLED_BACK')),
            source_path    TEXT NOT NULL,
            dest_path      TEXT,
            sha256         BLOB NOT NULL,
            keeper_path    TEXT,
            cross_volume   INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS scan_metadata (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('schema_version', '1');
        "#,
    )
    .map_err(|e| IndexError::Migration {
        version: 1,
        source: e,
    })
}
