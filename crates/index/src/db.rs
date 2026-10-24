use rusqlite::{Connection, OpenFlags};
use std::path::Path;
use crate::error::IndexError;
use crate::migrations;

/// Open (or create) the dedupe index at `path` with WAL mode enabled.
///
/// WAL mode is set on every connection open per E9 (eng review): a concurrent
/// reader can proceed while a writer holds its lock, which is required for
/// parallel scan workers.
pub fn open(path: &Path) -> Result<Connection, IndexError> {
    let conn = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
    migrations::run(&conn)?;
    Ok(conn)
}
