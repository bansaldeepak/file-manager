# Memory & CPU Baseline — Arcitae Dedupe

Date: 2026-10-24  
Build: v0.1.0, aarch64, release build  
Machine: Apple Silicon (M-series)

## Process breakdown (idle, no scan)

| Process | Memory | Notes |
|---------|--------|-------|
| Arcitae Dedupe (main) | ~358 MB | Rust backend + WKWebView host |
| tauri://localhost (renderer) | ~714–791 MB | WebKit rendering full-res images |
| Arcitae Dedupe Graphics and Media | ~17 MB | GPU/display compositing |
| Arcitae Dedupe Networking | ~6 MB | URLSession network process |
| **Total (1 instance)** | **~1.1 GB** | |

## Root cause of high renderer memory

`convertFileSrc` serves original full-resolution files directly to WKWebView.  
A grid of 30 × 20 MP HEIC/JPEG photos = each decoded to RGBA = ~300 MB per batch.  
WebKit keeps decoded bitmaps in the renderer process indefinitely.

## Planned fix

Generate Rust-side thumbnails (max 400 px on longest edge, JPEG quality 75).  
Serve a `thumbnail://` asset instead of the original file.  
Expected renderer memory reduction: **~80%** (750 MB → ~150 MB).

## Scan performance (30 K image library, M-series SSD)

| Phase | Time | Notes |
|-------|------|-------|
| Cold scan (no cache) | ~43 s | SHA-256 + pixel hash, rayon parallel |
| Warm scan (cache hit) | < 500 ms | Stat + mtime check only |
| UI load from cache | < 200 ms | SQLite → groups → render |

## Targets

| Metric | Current | Target |
|--------|---------|--------|
| Renderer memory (idle grid) | ~750 MB | < 150 MB |
| Renderer memory (after scroll) | unknown | < 200 MB |
| Cold scan 30 K | ~43 s | < 30 s |
| Warm scan / cache open | < 500 ms | < 200 ms |
| Binary size | 15.8 MB | < 20 MB ✓ |
