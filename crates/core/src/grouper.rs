use std::cmp::Reverse;
use std::collections::HashMap;

use crate::scanner::ScannedFile;

#[derive(Debug)]
pub struct DuplicateGroup {
    pub group_id: usize,
    pub match_type: MatchType,
    pub keeper: usize,
    pub files: Vec<usize>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum MatchType {
    Exact,
    PixelIdentical,
}

/// Build duplicate groups from scanned files.
///
/// Strategy: "exact subsumes pixel" — if a file is already in an exact-duplicate
/// group, it is excluded from pixel-identical groups. This prevents the same file
/// appearing in two groups, which would cause "ghost" entries after quarantine.
pub fn build_groups(files: &[ScannedFile]) -> Vec<DuplicateGroup> {
    let mut sha256_map: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
    let mut pixel_map: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();

    for (i, f) in files.iter().enumerate() {
        if let Some(h) = f.sha256 {
            sha256_map.entry(h.to_vec()).or_default().push(i);
        }
        if let Some(h) = f.pixel_hash {
            pixel_map.entry(h.to_vec()).or_default().push(i);
        }
    }

    // Any file index already in an exact group is excluded from pixel groups.
    let in_exact_group: std::collections::HashSet<usize> = sha256_map
        .values()
        .filter(|v| v.len() > 1)
        .flat_map(|v| v.iter().copied())
        .collect();

    let mut groups = Vec::new();
    let mut group_id = 0;

    for members in sha256_map.values().filter(|v| v.len() > 1) {
        let keeper = pick_keeper(files, members);
        groups.push(DuplicateGroup {
            group_id,
            match_type: MatchType::Exact,
            keeper,
            files: members.clone(),
        });
        group_id += 1;
    }

    for members in pixel_map.values().filter(|v| v.len() > 1) {
        let filtered: Vec<usize> = members
            .iter()
            .copied()
            .filter(|i| !in_exact_group.contains(i))
            .collect();
        if filtered.len() > 1 {
            let keeper = pick_keeper(files, &filtered);
            groups.push(DuplicateGroup {
                group_id,
                match_type: MatchType::PixelIdentical,
                keeper,
                files: filtered,
            });
            group_id += 1;
        }
    }

    groups
}

fn pick_keeper(files: &[ScannedFile], indices: &[usize]) -> usize {
    pick_keeper_with_roles(files, indices, &[])
}

/// Like `pick_keeper` but prefers files whose path starts with an "original" folder.
/// Tie-breaks within each tier: largest size, then lexicographically first path.
pub fn pick_keeper_with_roles(files: &[ScannedFile], indices: &[usize], original_dirs: &[&str]) -> usize {
    *indices
        .iter()
        .max_by_key(|&&i| {
            let f = &files[i];
            let path_str = f.path.to_string_lossy();
            let is_original = original_dirs.iter().any(|d| path_str.starts_with(*d));
            (is_original, f.size, Reverse(path_str.into_owned()))
        })
        .unwrap()
}

/// Build duplicate groups, biasing keeper selection toward files in `original_dirs`.
pub fn build_groups_with_roles(files: &[ScannedFile], original_dirs: &[&str]) -> Vec<DuplicateGroup> {
    let mut sha256_map: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
    let mut pixel_map: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();

    for (i, f) in files.iter().enumerate() {
        if let Some(h) = f.sha256 {
            sha256_map.entry(h.to_vec()).or_default().push(i);
        }
        if let Some(h) = f.pixel_hash {
            pixel_map.entry(h.to_vec()).or_default().push(i);
        }
    }

    let in_exact_group: std::collections::HashSet<usize> = sha256_map
        .values()
        .filter(|v| v.len() > 1)
        .flat_map(|v| v.iter().copied())
        .collect();

    let mut groups = Vec::new();
    let mut group_id = 0;

    for members in sha256_map.values().filter(|v| v.len() > 1) {
        let keeper = pick_keeper_with_roles(files, members, original_dirs);
        groups.push(DuplicateGroup {
            group_id,
            match_type: MatchType::Exact,
            keeper,
            files: members.clone(),
        });
        group_id += 1;
    }

    for members in pixel_map.values().filter(|v| v.len() > 1) {
        let filtered: Vec<usize> = members
            .iter()
            .copied()
            .filter(|i| !in_exact_group.contains(i))
            .collect();
        if filtered.len() > 1 {
            let keeper = pick_keeper_with_roles(files, &filtered, original_dirs);
            groups.push(DuplicateGroup {
                group_id,
                match_type: MatchType::PixelIdentical,
                keeper,
                files: filtered,
            });
            group_id += 1;
        }
    }

    groups
}
