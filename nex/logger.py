"""任务日志：写入 %APPDATA%/NEX/logs/<task_id>.log。"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .app_config import config_dir


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
