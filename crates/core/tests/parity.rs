use std::collections::HashMap;
use std::path::Path;
use serde::Deserialize;
use dedupe_core::{hash, pixel_hash};

#[derive(Deserialize)]
struct GoldenRecord {
    sha256: String,
    pixel_hash: String,
}

fn load_golden() -> HashMap<String, GoldenRecord> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../tests/fixtures/golden.json");
    let json = std::fs::read_to_string(path)
        .expect("golden.json missing — run: source .venv/bin/activate && python3 tests/fixtures/export_golden.py");
    serde_json::from_str(&json).unwrap()
}

fn fixtures_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/../../tests/fixtures/images"))
}

#[test]
fn sha256_matches_python() {
    let golden = load_golden();
    for (name, expected) in &golden {
        let path = fixtures_dir().join(name);
        let actual = hex::encode(hash::sha256_file(&path).unwrap());
        assert_eq!(actual, expected.sha256, "SHA-256 mismatch for {name}");
    }
}

#[test]
fn byte_identical_copies_have_same_sha256() {
    let golden = load_golden();
    let orig = golden.get("red_100x100.jpg").expect("fixture missing");
    let copy = golden.get("red_100x100_copy.jpg").expect("fixture missing");
    assert_eq!(orig.sha256, copy.sha256, "byte-identical copies must have the same SHA-256");
}

#[test]
fn pixel_hash_matches_python_for_lossless() {
    // PNG is lossless: Rust image crate and PIL produce identical RGBA bytes.
    let golden = load_golden();
    let png = golden.get("red_100x100.png").expect("PNG fixture missing");
    let path = fixtures_dir().join("red_100x100.png");
    let actual = hex::encode(pixel_hash::compute(&path).unwrap());
    assert_eq!(actual, png.pixel_hash, "pixel_hash mismatch for red_100x100.png");
}

#[test]
fn pixel_hash_same_for_byte_identical_copies() {
    // Both files must produce the same pixel_hash regardless of decoder.
    let path_orig = fixtures_dir().join("red_100x100.jpg");
    let path_copy = fixtures_dir().join("red_100x100_copy.jpg");
    let orig = hex::encode(pixel_hash::compute(&path_orig).unwrap());
    let copy = hex::encode(pixel_hash::compute(&path_copy).unwrap());
    assert_eq!(orig, copy, "byte-identical copies must have same pixel_hash");
}

#[test]
fn pixel_hash_differs_for_different_resolution() {
    let path_100 = fixtures_dir().join("red_100x100.jpg");
    let path_200 = fixtures_dir().join("red_200x200.jpg");
    let h100 = hex::encode(pixel_hash::compute(&path_100).unwrap());
    let h200 = hex::encode(pixel_hash::compute(&path_200).unwrap());
    assert_ne!(h100, h200, "different-resolution images must have different pixel_hash");
}

#[test]
fn huge_image_is_skipped_not_crashed() {
    let huge = fixtures_dir().join("huge_100000x100000.png");
    if !huge.exists() {
        return; // fixture not yet generated — skip silently
    }
    let result = pixel_hash::compute(&huge);
    assert!(result.is_err(), "huge image should return Err, not OOM crash");
    let msg = result.unwrap_err().to_string();
    assert!(
        msg.contains("exceed max") || msg.contains("dimensions"),
        "error should mention dimensions: {msg}"
    );
}
