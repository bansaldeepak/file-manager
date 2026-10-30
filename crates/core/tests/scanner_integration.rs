use dedupe_core::grouper::{build_groups, MatchType};
use dedupe_core::scanner::scan_directory;
use std::path::Path;

#[test]
fn scan_fixture_dir_finds_duplicates() {
    let fixtures = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../tests/fixtures/images"
    ));
    if !fixtures.exists() {
        return;
    }

    let files = scan_directory(fixtures, None, |_| {}).unwrap();
    assert!(!files.is_empty(), "expected at least one file");

    let groups = build_groups(&files);
    assert!(
        groups.iter().any(|g| g.match_type == MatchType::Exact),
        "expected at least one exact duplicate group"
    );
}

#[test]
fn scan_file_with_hash_error_records_error_not_panic() {
    let tmp = tempfile::tempdir().unwrap();
    let bad = tmp.path().join("bad.jpg");
    std::fs::write(&bad, b"not a jpeg").unwrap();

    let files = scan_directory(tmp.path(), None, |_| {}).unwrap();
    assert_eq!(files.len(), 1);
    assert!(files[0].sha256.is_some(), "sha256 should succeed on any readable file");
}

#[test]
fn scan_with_concurrency_1_produces_same_results() {
    let fixtures = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../tests/fixtures/images"
    ));
    if !fixtures.exists() {
        return;
    }

    let default_files = scan_directory(fixtures, None, |_| {}).unwrap();
    let serial_files = scan_directory(fixtures, Some(1), |_| {}).unwrap();

    assert_eq!(default_files.len(), serial_files.len());

    let mut default_paths: Vec<_> = default_files.iter().map(|f| f.path.clone()).collect();
    let mut serial_paths: Vec<_> = serial_files.iter().map(|f| f.path.clone()).collect();
    default_paths.sort();
    serial_paths.sort();
    assert_eq!(default_paths, serial_paths);
}
