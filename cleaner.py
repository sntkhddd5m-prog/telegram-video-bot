import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

class FileCleaner:
    def __init__(self, base_temp_dir: str = "/tmp/tg_video_bot"):
        self.base_temp_dir = base_temp_dir
        os.makedirs(self.base_temp_dir, exist_ok=True)

    @contextmanager
    def create_task_dir(self, prefix: str = "task_") -> Generator[str, None, None]:
        task_dir = tempfile.mkdtemp(prefix=prefix, dir=self.base_temp_dir)
        try:
            yield task_dir
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

    def cleanup_stale_files(self, max_age_seconds: int = 1800) -> int:
        if not os.path.exists(self.base_temp_dir):
            return 0
        now = time.time()
        count = 0
        for entry in os.scandir(self.base_temp_dir):
            try:
                if now - entry.stat().st_mtime > max_age_seconds:
                    if entry.is_dir():
                        shutil.rmtree(entry.path, ignore_errors=True)
                    else:
                        os.remove(entry.path)
                    count += 1
            except Exception:
                pass
        return count

file_cleaner = FileCleaner()
