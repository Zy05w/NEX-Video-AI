"""任务日志：写入 %APPDATA%/NEX/logs/<task_id>.log。"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .app_config import config_dir


def cleanup_old_logs(days: int, log_dir: Path | None = None) -> int:
    """删除超过保留天数的任务日志。"""
    if days <= 0:
        return 0
    base = log_dir if log_dir is not None else config_dir() / "logs"
    if not base.exists():
        return 0
    cutoff = time.time() - days * 86400
    removed = 0
    for path in base.glob("*.log"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


class TaskLogger:
    def __init__(
        self,
        task_id: str,
        log_dir: Path | None = None,
        on_line: Optional[Callable[[str], None]] = None,
    ):
        base = log_dir if log_dir is not None else config_dir() / "logs"
        base.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.path = base / f"{task_id}.log"
        self.on_line = on_line
        try:
            self.path.write_text("", encoding="utf-8")
        except OSError:
            pass
        engine_log = self.path.with_name(f"{self.path.stem}.engine.log")
        try:
            engine_log.unlink()
        except OSError:
            pass
        self._fh = open(self.path, "a", encoding="utf-8", buffering=1)
        self._lock = threading.Lock()

    def log(self, stage: str, message: str) -> str:
        line = f"{datetime.now().strftime('%H:%M:%S')} [{stage}] {message}"
        with self._lock:
            try:
                self._fh.write(line + "\n")
            except (OSError, ValueError):
                pass
        if self.on_line is not None:
            try:
                self.on_line(line)
            except Exception:
                pass
        return line

    def close(self) -> None:
        try:
            self._fh.close()
        except (OSError, ValueError):
            pass
