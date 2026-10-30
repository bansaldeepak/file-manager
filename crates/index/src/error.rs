use thiserror::Error;

#[derive(Debug, Error)]
pub enum IndexError {
    #[error("SQLite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("Migration failed at version {version}: {source}")]
    Migration { version: u32, source: rusqlite::Error },
    #[error("Database full — free disk space and retry")]
    DiskFull,
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Promote a rusqlite error to IndexError, converting SQLITE_FULL → IndexError::DiskFull.
/// All other error codes map to IndexError::Sqlite.
pub fn promote(e: rusqlite::Error) -> IndexError {
    match &e {
        rusqlite::Error::SqliteFailure(err, _)
            if err.code == rusqlite::ErrorCode::DiskFull =>
        {
            IndexError::DiskFull
        }
        _ => IndexError::Sqlite(e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn promote_converts_disk_full() {
        let ffi_err = rusqlite::ffi::Error {
            code: rusqlite::ErrorCode::DiskFull,
            extended_code: 13,
        };
        let sql_err = rusqlite::Error::SqliteFailure(
            ffi_err,
            Some("database or disk is full".to_string()),
        );
        let promoted = promote(sql_err);
        assert!(matches!(promoted, IndexError::DiskFull));
    }

    #[test]
    fn promote_keeps_other_errors() {
        let ffi_err = rusqlite::ffi::Error {
            code: rusqlite::ErrorCode::NotFound,
            extended_code: 0,
        };
        let sql_err = rusqlite::Error::SqliteFailure(ffi_err, None);
        let promoted = promote(sql_err);
        assert!(matches!(promoted, IndexError::Sqlite(_)));
    }
}
