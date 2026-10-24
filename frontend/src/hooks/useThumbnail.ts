import { invoke } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';

// Resolved data URLs — prevents re-requesting the same image
const resolved = new Map<string, string>();

// In-flight promises — prevents duplicate concurrent requests for the same key
const inflight = new Map<string, Promise<string>>();

// Soft concurrency cap on the JS side — limits simultaneous invoke calls
// (Rust has its own hard cap of 4 via Semaphore)
const MAX_JS_CONCURRENT = 8;
let activeCount = 0;
const queue: Array<() => void> = [];

function drain() {
  while (queue.length > 0 && activeCount < MAX_JS_CONCURRENT) {
    activeCount++;
    queue.shift()!();
  }
}

function withConcurrencyLimit<T>(fn: () => Promise<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const run = () => {
      fn()
        .then(resolve, reject)
        .finally(() => {
          activeCount--;
          drain();
        });
    };
    if (activeCount < MAX_JS_CONCURRENT) {
      activeCount++;
      run();
    } else {
      queue.push(run);
    }
  });
}

export function useThumbnail(path: string, maxPx: number): string {
  const key = `${path}@${maxPx}`;
  const [src, setSrc] = useState<string>(() => resolved.get(key) ?? '');

  useEffect(() => {
    if (!path) return;

    const cached = resolved.get(key);
    if (cached) {
      setSrc(cached);
      return;
    }

    let cancelled = false;

    // Reuse an already-in-flight request for the same key
    const existing = inflight.get(key);
    const req = existing ?? withConcurrencyLimit(() =>
      invoke<string>('get_thumbnail', { path, maxPx })
    );

    if (!existing) inflight.set(key, req);

    req
      .then(dataUrl => {
        resolved.set(key, dataUrl);
        inflight.delete(key);
        if (!cancelled) setSrc(dataUrl);
      })
      .catch(() => {
        inflight.delete(key);
      });

    return () => { cancelled = true; };
  }, [key, path, maxPx]);

  return src;
}
