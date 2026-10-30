use std::path::Path;
use tracing_appender::rolling::{RollingFileAppender, Rotation};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

pub struct LogGuard {
    _guard: tracing_appender::non_blocking::WorkerGuard,
}

/// Initialize file-based logging with daily rotation.
///
/// Keeps at most 7 daily log files; older ones are deleted at startup.
/// File paths are only logged at DEBUG level (not INFO) to avoid exposing
/// personal photo paths in the log file.
///
/// Returns a guard that must be held alive for the duration of the process;
/// dropping it flushes the async log buffer.
pub fn init(log_dir: &Path) -> LogGuard {
    std::fs::create_dir_all(log_dir).ok();
    cleanup_old_logs(log_dir, 7);

    let file_appender = RollingFileAppender::new(Rotation::DAILY, log_dir, "dedupe.log");
    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    tracing_subscriber::registry()
        .with(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("info,dedupe_core=debug")),
        )
        .with(
            fmt::layer()
                .with_writer(non_blocking)
                .with_ansi(false),
        )
        .init();

    LogGuard { _guard: guard }
}

fn cleanup_old_logs(log_dir: &Path, keep_days: u64) {
    let cutoff = std::time::SystemTime::now()
        .checked_sub(std::time::Duration::from_secs(keep_days * 24 * 3600))
        .unwrap_or(std::time::UNIX_EPOCH);

    let Ok(entries) = std::fs::read_dir(log_dir) else {
        return;
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if !name.starts_with("dedupe.log") {
            continue;
        }
        if let Ok(meta) = entry.metadata() {
            if let Ok(modified) = meta.modified() {
                if modified < cutoff {
                    std::fs::remove_file(entry.path()).ok();
                }
            }
        }
    }
}
