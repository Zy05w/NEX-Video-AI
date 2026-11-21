"""任务日志：写入 %APPDATA%/NEX/logs/<task_id>.log。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .app_config import config_dir


class TaskLogger:
    def __init__(self, task_id: str, log_dir: Path | None = None):
        base = log_dir if log_dir is not None else config_dir() / "logs"
        base.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.path = base / f"{task_id}.log"
        try:
            self.path.write_text("", encoding="utf-8")
        except OSError:
            pass
        self._fh = open(self.path, "a", encoding="utf-8", buffering=1)

    def log(self, stage: str, message: str) -> str:
        line = f"{datetime.now().strftime('%H:%M:%S')} [{stage}] {message}"
        try:
            self._fh.write(line + "\n")
        except (OSError, ValueError):
            pass
        return line

    def close(self) -> None:
        try:
            self._fh.close()
        except (OSError, ValueError):
            pass
