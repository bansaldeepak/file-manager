use std::sync::{Arc, Condvar, Mutex, OnceLock};

struct Inner {
    count: Mutex<usize>,
    cvar: Condvar,
}

pub struct DecodeSemaphore(Arc<Inner>);

pub struct Permit(Arc<Inner>);

impl Drop for Permit {
    fn drop(&mut self) {
        let mut n = self.0.count.lock().unwrap();
        *n += 1;
        self.0.cvar.notify_one();
    }
}

impl DecodeSemaphore {
    fn new(cap: usize) -> Self {
        Self(Arc::new(Inner {
            count: Mutex::new(cap),
            cvar: Condvar::new(),
        }))
    }

    pub fn acquire(&self) -> Permit {
        let mut n = self.0.count.lock().unwrap();
        while *n == 0 {
            n = self.0.cvar.wait(n).unwrap();
        }
        *n -= 1;
        Permit(Arc::clone(&self.0))
    }

    pub fn available_permits(&self) -> usize {
        *self.0.count.lock().unwrap()
    }
}

static DECODE_SEM: OnceLock<DecodeSemaphore> = OnceLock::new();

pub fn semaphore() -> &'static DecodeSemaphore {
    DECODE_SEM.get_or_init(|| {
        let cap = num_cpus().min(4).max(2);
        DecodeSemaphore::new(cap)
    })
}

fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(2)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn semaphore_cap_is_2_to_4() {
        let cap = semaphore().available_permits();
        assert!(cap >= 2 && cap <= 4, "cap={cap} not in [2,4]");
    }
}
