"""后台工作线程：顺序消费任务队列并驱动处理管线。"""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .db import TaskRepository
from .engines import CancelledError, EngineError
from .i18n import t
from .pipeline import (
    EncodeOptions,
    FIOptions,
    PipelineError,
    PipelineOptions,
    SROptions,
    run_pipeline,
)
from .task import Task, TaskStatus


class PipelineWorker(QThread):
    taskStarted = Signal(str)
    taskProgress = Signal(str, int, str, str)  # id, percent, stage, message
    taskLog = Signal(str, str)                 # id, line
    taskFinished = Signal(str, str, str)       # id, outcome(done/failed/cancelled), message

    def __init__(self, repo: TaskRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._cancel_events: dict[str, threading.Event] = {}
        self._queued: set[str] = set()
        self._current_id: str | None = None

    # ---------- 对外接口 ----------
    def enqueue(self, task_id: str) -> None:
        with self._lock:
            if task_id in self._queued:
                return
            self._queued.add(task_id)
        self._queue.put(task_id)
        if not self.isRunning():
            self.start()

    def cancel_task(self, task_id: str) -> None:
        with self._lock:
            event = self._cancel_events.get(task_id)
        if event is not None:
            event.set()

    @property
    def current_task_id(self) -> str | None:
        with self._lock:
            return self._current_id

    @property
    def is_busy(self) -> bool:
        return self.current_task_id is not None

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            events = list(self._cancel_events.values())
        for event in events:
            event.set()

    # ---------- 线程主循环 ----------
    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                task_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            with self._lock:
                self._queued.discard(task_id)
            if self._stop_event.is_set():
                break
            task = self.repo.get(task_id)
            if task is None or task.status != TaskStatus.PENDING:
                continue
            self._run_task(task)

    def _run_task(self, task: Task) -> None:
        cancel = threading.Event()
        with self._lock:
            self._cancel_events[task.id] = cancel
            self._current_id = task.id

        task.status = TaskStatus.RUNNING
        task.progress = 0
        task.stage = ""
        task.started_at = time.time()
        task.finished_at = None
        task.output_path = ""
        task.error = ""
        self.repo.update(task)
        self.taskStarted.emit(task.id)

        last = {"percent": -1, "stage": ""}

        def on_progress(stage: str, percent: float, message: str) -> None:
            pct = max(0, min(100, int(percent)))
            if pct == last["percent"] and stage == last["stage"]:
                return
            last["percent"] = pct
            last["stage"] = stage
            task.progress = pct
            task.stage = stage
            self.repo.update_progress(task.id, pct, stage)
            self.taskProgress.emit(task.id, pct, stage, message)

        def on_log(line: str) -> None:
            self.taskLog.emit(task.id, line)

        options = self._build_options(task)
        try:
            result = run_pipeline(
                options, on_progress=on_progress, cancel=cancel, on_log=on_log
            )
        except CancelledError as exc:
            task.status = TaskStatus.CANCELLED
            task.stage = "已取消"
            task.finished_at = time.time()
            task.log_path = getattr(exc, "log_path", "") or task.log_path
            self.repo.update(task)
            self.taskFinished.emit(task.id, "cancelled", t("任务已取消"))
        except (EngineError, PipelineError) as exc:
            task.status = TaskStatus.FAILED
            task.stage = "失败"
            message = exc.short() if isinstance(exc, EngineError) else str(exc)
            task.error = message
            task.finished_at = time.time()
            task.log_path = getattr(exc, "log_path", "") or task.log_path
            self.repo.update(task)
            self.taskFinished.emit(task.id, "failed", message)
        except Exception as exc:  # 防御：不应发生的内部错误
            task.status = TaskStatus.FAILED
            task.stage = "失败"
            task.error = t("内部错误：{error}", error=exc)
            task.finished_at = time.time()
            self.repo.update(task)
            self.taskFinished.emit(task.id, "failed", task.error)
        else:
            task.status = TaskStatus.DONE
            task.progress = 100
            task.stage = "完成"
            task.finished_at = time.time()
            task.output_path = str(result.output_path)
            task.log_path = str(result.log_path)
            self.repo.update(task)
            self.taskProgress.emit(task.id, 100, "完成", "")
            self.taskFinished.emit(task.id, "done", "")
        finally:
            with self._lock:
                self._cancel_events.pop(task.id, None)
                self._current_id = None

    @staticmethod
    def _build_options(task: Task) -> PipelineOptions:
        params = task.params
        return PipelineOptions(
            input_path=Path(params.input_path),
            task_id=task.id,
            output_dir=Path(params.output_dir) if params.output_dir else None,
            sr=SROptions(
                enabled=params.sr_enabled,
                model=params.sr_model,
                scale=params.sr_scale,
                target_height=params.sr_height,
            ),
            fi=FIOptions(
                enabled=params.fi_enabled,
                model=params.fi_model,
                multiplier=params.fi_mult,
                target_fps=params.fi_fps,
            ),
            encode=EncodeOptions(
                encoder=params.encoder,
                crf=params.crf,
                preset=params.preset,
            ),
            gpu_id=params.gpu_id,
            keep_temp=params.keep_temp,
            temp_guard=params.temp_limit > 0,
            temp_limit=params.temp_limit,
        )
