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
        let keeper = pick_keeper(files, members);
        groups.push(DuplicateGroup {
            group_id,
            match_type: MatchType::PixelIdentical,
            keeper,
            files: members.clone(),
        });
        group_id += 1;
    }

    groups
}

fn pick_keeper(files: &[ScannedFile], indices: &[usize]) -> usize {
    *indices
        .iter()
        .max_by_key(|&&i| {
            let f = &files[i];
            (f.size, Reverse(f.path.to_string_lossy().into_owned()))
        })
        .unwrap()
}
