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
