use std::path::PathBuf;
use dedupe_index::{db, Connection, IndexError};

#[derive(Debug, PartialEq)]
enum MigrationChoice {
    Reset,
    Quit,
}

/// Open the dedupe index, showing a blocking dialog on migration failure.
///
/// If migration fails:
/// - Offers "Reset Cache" (delete DB and retry — safe, cache is derived data only)
/// - Or "Quit" (exit 1)
///
/// This runs before Tauri's main window is created, so we use `rfd` for the
/// native dialog rather than the Tauri plugin dialog API.
pub fn init_database(db_path: &PathBuf) -> Result<Connection, String> {
    match db::open(db_path) {
        Ok(conn) => Ok(conn),
        Err(IndexError::Migration { version, source }) => {
            let message = format!(
                "Database migration to version {} failed:\n{}\n\n\
                Choose \"Reset Cache\" to delete the scan cache and retry \
                (your photos are not affected), or \"Quit\" to exit.",
                version, source
            );
            let choice = show_migration_dialog(&message);
            if choice == MigrationChoice::Reset {
                std::fs::remove_file(db_path).ok();
                db::open(db_path).map_err(|e| format!("Failed to reopen after reset: {e}"))
            } else {
                std::process::exit(1);
            }
        }
        Err(e) => Err(format!("Failed to open database: {e}")),
    }
}

fn show_migration_dialog(message: &str) -> MigrationChoice {
    let confirmed = rfd::MessageDialog::new()
        .set_title("Database Error")
        .set_description(message)
        .set_buttons(rfd::MessageButtons::OkCancelCustom(
            "Reset Cache".into(),
            "Quit".into(),
        ))
        .set_level(rfd::MessageLevel::Error)
        .show();
    match confirmed {
        rfd::MessageDialogResult::Ok | rfd::MessageDialogResult::Custom(_) => {
            MigrationChoice::Reset
        }
        _ => MigrationChoice::Quit,
    }
}

#[cfg(test)]
mod tests {
    use dedupe_index::IndexError;

    #[test]
    fn migration_error_is_recognizable() {
        let err = IndexError::Migration {
            version: 2,
            source: dedupe_index::rusqlite::Error::InvalidQuery,
        };
        assert!(matches!(err, IndexError::Migration { .. }));
    }
}
