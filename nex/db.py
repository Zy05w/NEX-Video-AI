"""SQLite 任务持久化（%APPDATA%/NEX/nex.db）。"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .app_config import config_dir
from .i18n import t
from .task import Task, TaskStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    output_path TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    log_path TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
"""


class TaskRepository:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else config_dir() / "nex.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            conn.commit()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add(self, task: Task) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO tasks (id, data, status, progress, stage, created_at,"
                " started_at, finished_at, output_path, error, log_path)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task.id, task.to_data_json(), task.status.value,
                    task.progress, task.stage, task.created_at,
                    task.started_at, task.finished_at,
                    task.output_path, task.error, task.log_path,
                ),
            )
            conn.commit()

    def update(self, task: Task) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET data=?, status=?, progress=?, stage=?,"
                " started_at=?, finished_at=?, output_path=?, error=?, log_path=?"
                " WHERE id=?",
                (
                    task.to_data_json(), task.status.value, task.progress,
                    task.stage, task.started_at, task.finished_at,
                    task.output_path, task.error, task.log_path, task.id,
                ),
            )
            conn.commit()

    def update_progress(self, task_id: str, progress: int, stage: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET progress=?, stage=? WHERE id=?",
                (max(0, min(100, int(progress))), stage, task_id),
            )
            conn.commit()

    def delete(self, task_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()

    def get(self, task_id: str) -> Task | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
        return _row_to_task(row) if row is not None else None

    def list_all(self) -> list[Task]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_task(row) for row in rows]

    def list_pending(self) -> list[Task]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY created_at ASC",
                (TaskStatus.PENDING.value,),
            ).fetchall()
        return [_row_to_task(row) for row in rows]

    def recover_running(self) -> int:
        """应用重启后把遗留的'处理中'恢复为'等待中'。"""
        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status=?, progress=0, stage='' WHERE status=?",
                (TaskStatus.PENDING.value, TaskStatus.RUNNING.value),
            )
            conn.commit()
            return cursor.rowcount


def _row_to_task(row: sqlite3.Row) -> Task:
    try:
        file_name, params = Task.from_data_json(row["data"])
    except (ValueError, TypeError):
        file_name, params = "", None
    if params is None:
        raise ValueError(t("任务数据损坏：{id}", id=row["id"]))
    try:
        status = TaskStatus(row["status"])
    except ValueError:
        status = TaskStatus.PENDING
    return Task(
        id=row["id"],
        file_name=file_name,
        params=params,
        status=status,
        progress=int(row["progress"] or 0),
        stage=row["stage"] or "",
        created_at=float(row["created_at"] or 0),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        output_path=row["output_path"] or "",
        error=row["error"] or "",
        log_path=row["log_path"] or "",
    )
