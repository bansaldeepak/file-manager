use dedupe_core::grouper::{build_groups, MatchType};
use dedupe_core::scanner::ScannedFile;
use std::path::PathBuf;

fn make_file(path: &str, sha256: Option<[u8; 32]>, pixel_hash: Option<[u8; 32]>) -> ScannedFile {
    ScannedFile {
        path: PathBuf::from(path),
        size: 1000,
        mtime_ns: 0,
        sha256,
        pixel_hash,
        error: None,
    }
}

#[test]
fn exact_subsumes_pixel() {
    // A and B are exact duplicates (same SHA-256)
    // B and C share pixel_hash (different SHA-256)
    // B is in exact group → must NOT appear in pixel group
    let sha_ab = [1u8; 32];
    let pixel_bc = [2u8; 32];
    let sha_c = [3u8; 32];

    let files = vec![
        make_file("/a.jpg", Some(sha_ab), Some([10u8; 32])),
        make_file("/b.jpg", Some(sha_ab), Some(pixel_bc)),
        make_file("/c.jpg", Some(sha_c), Some(pixel_bc)),
    ];

    let groups = build_groups(&files);

    let exact: Vec<_> = groups.iter().filter(|g| g.match_type == MatchType::Exact).collect();
    let pixel: Vec<_> = groups.iter().filter(|g| g.match_type == MatchType::PixelIdentical).collect();

    assert_eq!(exact.len(), 1, "expected 1 exact group");

    // B (index 1) must not appear in any pixel group
    let b_in_pixel = pixel.iter().any(|g| g.files.contains(&1));
    assert!(!b_in_pixel, "B (in exact group) must not appear in pixel group");

    // After B is excluded from the pixel group, only C remains — not a group of 2, so no pixel group
    assert_eq!(pixel.len(), 0, "pixel group should be dropped when it has only 1 non-exact member");
}

#[test]
fn pure_pixel_group_shown_when_no_exact_overlap() {
    // D and E share only pixel_hash, no exact match
    let pixel_de = [4u8; 32];

    let files = vec![
        make_file("/d.jpg", Some([5u8; 32]), Some(pixel_de)),
        make_file("/e.jpg", Some([6u8; 32]), Some(pixel_de)),
    ];

    let groups = build_groups(&files);
    let pixel: Vec<_> = groups.iter().filter(|g| g.match_type == MatchType::PixelIdentical).collect();
    assert_eq!(pixel.len(), 1, "should show pixel group when no exact overlap");
}

#[test]
fn no_groups_for_unique_files() {
    let files = vec![
        make_file("/x.jpg", Some([7u8; 32]), Some([8u8; 32])),
        make_file("/y.jpg", Some([9u8; 32]), Some([10u8; 32])),
    ];
    assert!(build_groups(&files).is_empty());
}
