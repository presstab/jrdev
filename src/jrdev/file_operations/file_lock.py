import os
import sys
import time
from pathlib import Path

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

class FileLock:
    """
    Cross-platform file lock for safe concurrent file access.
    Use as a context manager:
        with FileLock(path):
            ...
    """
    def __init__(self, path, timeout=10, delay=0.05):
        self.lockfile = Path(str(path))
        self.timeout = timeout
        self.delay = delay
        self._fh = None

    def acquire(self):
        start_time = time.time()
        while True:
            try:
                self._fh = open(self.lockfile, 'a+')
                if os.name == 'nt':
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Lock acquired
                break
            except (IOError, OSError):
                if self._fh:
                    self._fh.close()
                if (time.time() - start_time) >= self.timeout:
                    raise TimeoutError(f"Timeout occurred trying to acquire lock for {self.lockfile}")
                time.sleep(self.delay)

    def release(self):
        if self._fh:
            try:
                if os.name == 'nt':
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
