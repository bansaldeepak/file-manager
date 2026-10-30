use rusqlite::{Connection, OptionalExtension};
use crate::error::{IndexError, promote};

pub struct FileCacheRecord<'a> {
    pub path: &'a str,
    pub size: i64,
    pub mtime_ns: i64,
    pub analyzer_version: i32,
    pub sha256: Option<&'a [u8]>,
    pub pixel_hash: Option<&'a [u8]>,
    pub error: Option<&'a str>,
}

pub fn upsert(conn: &Connection, rec: &FileCacheRecord) -> Result<(), IndexError> {
    conn.execute(
        "INSERT OR REPLACE INTO file_cache
         (path, size, mtime_ns, analyzer_version, sha256, pixel_hash, error, scanned_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, datetime('now'))",
        rusqlite::params![
            rec.path,
            rec.size,
            rec.mtime_ns,
            rec.analyzer_version,
            rec.sha256,
            rec.pixel_hash,
            rec.error
        ],
    )
    .map_err(promote)?;
    Ok(())
}

#[derive(Debug)]
pub struct CachedFile {
    pub id: i64,
    pub path: String,
    pub size: i64,
    pub mtime_ns: i64,
    pub sha256: Option<Vec<u8>>,
    pub pixel_hash: Option<Vec<u8>>,
    pub error: Option<String>,
}

pub fn load_all(conn: &Connection) -> Result<Vec<CachedFile>, IndexError> {
    let mut stmt = conn
        .prepare(
            "SELECT id, path, size, mtime_ns, sha256, pixel_hash, error
             FROM file_cache ORDER BY path",
        )
        .map_err(promote)?;
    let rows = stmt
        .query_map([], |row| {
            Ok(CachedFile {
                id: row.get(0)?,
                path: row.get(1)?,
                size: row.get(2)?,
                mtime_ns: row.get(3)?,
                sha256: row.get(4)?,
                pixel_hash: row.get(5)?,
                error: row.get(6)?,
            })
        })
        .map_err(promote)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(promote)
}

pub fn get_scanned_at(conn: &Connection) -> Option<String> {
    conn.query_row(
        "SELECT value FROM scan_metadata WHERE key = 'last_scan_at'",
        [],
        |r| r.get(0),
    )
    .ok()
}

pub fn set_scanned_at(conn: &Connection) -> Result<(), IndexError> {
    conn.execute(
        "INSERT OR REPLACE INTO scan_metadata (key, value) VALUES ('last_scan_at', datetime('now'))",
        [],
    )
    .map_err(promote)?;
    Ok(())
}

pub fn get_by_path(conn: &Connection, path: &str) -> Result<Option<CachedFile>, IndexError> {
    conn.query_row(
        "SELECT id, path, size, mtime_ns, sha256, pixel_hash, error
         FROM file_cache WHERE path = ?1",
        [path],
        |row| {
            Ok(CachedFile {
                id: row.get(0)?,
                path: row.get(1)?,
                size: row.get(2)?,
                mtime_ns: row.get(3)?,
                sha256: row.get(4)?,
                pixel_hash: row.get(5)?,
                error: row.get(6)?,
            })
        },
    )
    .optional()
    .map_err(promote)
}
