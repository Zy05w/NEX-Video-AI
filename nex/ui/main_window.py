"""主窗口：任务队列、处理控制与日志。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    MessageBox,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SubtitleLabel,
    TextEdit,
)

from .. import APP_NAME
from ..app_config import AppConfig, config_dir
from ..db import TaskRepository
from ..logger import cleanup_old_logs
from ..pipeline import cleanup_stale_temp
from ..task import Task, TaskParams, TaskStatus, new_task
from ..worker import PipelineWorker
from .add_task_dialog import AddTaskDialog
from .settings_dialog import SettingsDialog
from .task_table import TaskTableWidget


class MainWindow(QMainWindow):
    def __init__(self, repo: TaskRepository | None = None):
        super().__init__()
        self.config = AppConfig.load()
        self.repo = repo if repo is not None else TaskRepository()
        cleanup_stale_temp()
        cleanup_old_logs(self.config.log_keep_days)
        recovered = self.repo.recover_running()
        self._selected_task_id: str | None = None

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 760)
        self.setMinimumSize(960, 600)
        self._build_ui()
        self._load_tasks()

        self.worker = PipelineWorker(self.repo, self)
        self.worker.taskStarted.connect(self._on_task_started)
        self.worker.taskProgress.connect(self._on_task_progress)
        self.worker.taskLog.connect(self._on_task_log)
        self.worker.taskFinished.connect(self._on_task_finished)

        if recovered:
            self.statusBar().showMessage(
                f"已恢复 {recovered} 个未完成任务为等待中", 6000
            )

    # ---------- 界面构建 ----------
    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        toolbar = QWidget(central)
        toolbar.setObjectName("toolbar")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = SubtitleLabel(APP_NAME, toolbar)
        subtitle = CaptionLabel("AI 视频超分 · 补帧", toolbar)
        subtitle.setStyleSheet("color: #6B7280;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        bar.addLayout(title_box)
        bar.addStretch(1)

        self.addBtn = PrimaryPushButton(toolbar)
        self.addBtn.setText("添加任务")
        self.addBtn.setIcon(FIF.ADD)
        self.addBtn.clicked.connect(self._on_add_task)

        self.startBtn = PushButton(toolbar)
        self.startBtn.setText("开始全部")
        self.startBtn.setIcon(FIF.PLAY)
        self.startBtn.clicked.connect(self._on_start_all)

        self.settingsBtn = PushButton(toolbar)
        self.settingsBtn.setText("设置")
        self.settingsBtn.setIcon(FIF.SETTING)
        self.settingsBtn.clicked.connect(self._on_settings)

        bar.addWidget(self.addBtn)
        bar.addWidget(self.startBtn)
        bar.addWidget(self.settingsBtn)
        root.addWidget(toolbar)

        self.table = TaskTableWidget(central)
        self.table.taskSelected.connect(self._on_task_selected)
        self.table.cancelRequested.connect(self._on_cancel_requested)
        self.table.retryRequested.connect(self._on_retry_requested)
        self.table.deleteRequested.connect(self._on_delete_requested)
        root.addWidget(self.table, 1)

        log_panel = QWidget(central)
        log_panel.setObjectName("logPanel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_layout.setSpacing(6)

        log_header = QHBoxLayout()
        self.logTitle = StrongBodyLabel("日志 · 未选择任务", log_panel)
        clear_btn = PushButton(log_panel)
        clear_btn.setText("清空视图")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_log_view)
        log_header.addWidget(self.logTitle)
        log_header.addStretch(1)
        log_header.addWidget(clear_btn)
        log_layout.addLayout(log_header)

        self.logEdit = TextEdit(log_panel)
        self.logEdit.setReadOnly(True)
        self.logEdit.setMinimumHeight(140)
        self.logEdit.setMaximumHeight(180)
        self.logEdit.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.logEdit)
        root.addWidget(log_panel)

        self.statusBar().showMessage("就绪")

    def _load_tasks(self) -> None:
        tasks = self.repo.list_all()
        for task in tasks:
            self.table.add_task(task)
        if tasks:
            self.table.selectRow(0)
            self._on_task_selected(tasks[0])
        self.statusBar().showMessage(f"就绪 · 共 {len(tasks)} 个任务")

    # ---------- 任务操作 ----------
    def _on_add_task(self) -> None:
        dialog = AddTaskDialog(self)
        if not dialog.exec() or dialog.request is None:
            return
        request = dialog.request
        added: list[Task] = []
        for path in request.files:
            params = TaskParams(
                input_path=path,
                output_dir=request.output_dir or self.config.output_dir,
                sr_enabled=request.sr_enabled,
                sr_model=request.sr_model,
                sr_scale=request.sr_scale,
                sr_height=request.sr_height,
                fi_enabled=request.fi_enabled,
                fi_model=request.fi_model,
                fi_mult=request.fi_mult,
                fi_fps=request.fi_fps,
                encoder=self.config.encoder,
                gpu_id=self.config.gpu_id,
                temp_limit=self.config.temp_limit,
            )
            task = new_task(params)
            self.repo.add(task)
            self.table.add_task(task)
            added.append(task)
        if not added:
            return
        self.table.selectRow(self.table.rowCount() - 1)
        if request.start_now:
            for task in added:
                self.worker.enqueue(task.id)
        self.statusBar().showMessage(f"已添加 {len(added)} 个任务", 4000)

    def _on_start_all(self) -> None:
        pending = self.repo.list_pending()
        for task in pending:
            self.worker.enqueue(task.id)
        if pending:
            self.statusBar().showMessage(f"已开始 {len(pending)} 个任务", 4000)
        else:
            self.statusBar().showMessage("没有等待中的任务", 3000)

    def _on_cancel_requested(self, task_id: str) -> None:
        task = self.table.task_by_id(task_id)
        if task is None:
            return
        if task.status == TaskStatus.RUNNING:
            self.worker.cancel_task(task_id)
            self.statusBar().showMessage("正在取消任务...", 3000)
        elif task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.stage = "已取消"
            self.repo.update(task)
            self.table.update_task(task)
            self.statusBar().showMessage(f"已取消：{task.file_name}", 4000)

    def _on_retry_requested(self, task_id: str) -> None:
        task = self.repo.get(task_id)
        if task is None or task.status not in (
            TaskStatus.FAILED, TaskStatus.CANCELLED
        ):
            return
        task.status = TaskStatus.PENDING
        task.progress = 0
        task.stage = ""
        task.error = ""
        task.output_path = ""
        task.started_at = None
        task.finished_at = None
        self.repo.update(task)
        self.table.update_task(task)
        self.worker.enqueue(task.id)
        self.statusBar().showMessage(f"已重新加入队列：{task.file_name}", 4000)

    def _on_delete_requested(self, task_id: str) -> None:
        task = self.table.task_by_id(task_id)
        if task is None:
            return
        if task.status == TaskStatus.RUNNING:
            MessageBox(
                "无法删除",
                "任务正在处理中，请先取消后再删除。",
                self,
            ).exec()
            return
        box = MessageBox(
            "删除任务记录",
            f"确定删除「{task.file_name}」的记录吗？\n仅删除记录，不会删除视频文件。",
            self,
        )
        if box.exec():
            self.repo.delete(task_id)
            self.table.remove_task(task_id)
            if self._selected_task_id == task_id:
                self._selected_task_id = None
                self.logTitle.setText("日志 · 未选择任务")
                self.logEdit.clear()
            self.statusBar().showMessage("已删除任务记录", 3000)

    def _on_settings(self) -> None:
        SettingsDialog(self.config, self).exec()

    # ---------- 工作线程信号 ----------
    def _on_task_started(self, task_id: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        self.table.update_task(task)
        self.statusBar().showMessage(f"正在处理：{task.file_name}")
        if task_id == self._selected_task_id:
            self.logTitle.setText(f"日志 · {task.file_name}")

    def _on_task_progress(
        self, task_id: str, percent: int, stage: str, message: str
    ) -> None:
        self.table.set_progress(task_id, percent, stage)
        if task_id == self._selected_task_id:
            self.statusBar().showMessage(f"处理中：{stage} · {percent}%")

    def _on_task_log(self, task_id: str, line: str) -> None:
        if task_id == self._selected_task_id:
            self.logEdit.append(line)

    def _on_task_finished(self, task_id: str, outcome: str, message: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        self.table.update_task(task)
        if outcome == "done":
            text = f"已完成：{task.file_name}"
        elif outcome == "failed":
            text = f"失败：{task.file_name} — {message[:80]}"
        else:
            text = f"已取消：{task.file_name}"
        self.statusBar().showMessage(text, 10000)
        if task_id == self._selected_task_id:
            self._show_task_log(task)

    # ---------- 日志 ----------
    def _on_task_selected(self, task: Task) -> None:
        self._selected_task_id = task.id
        latest = self.repo.get(task.id) or task
        self._show_task_log(latest)

    def _show_task_log(self, task: Task) -> None:
        self.logTitle.setText(f"日志 · {task.file_name}")
        self.logEdit.clear()
        path = (
            Path(task.log_path)
            if task.log_path
            else config_dir() / "logs" / f"{task.id}.log"
        )
        lines: list[str] = []
        try:
            if path.exists():
                lines = path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
        except OSError:
            lines = []
        if not lines and task.error:
            lines = [f"[错误] {task.error}"]
        if not lines:
            lines = [f"（暂无日志）目标参数：{task.summary}"]
        for line in lines[-300:]:
            self.logEdit.append(line)

    def _clear_log_view(self) -> None:
        self.logEdit.clear()

    # ---------- 关闭 ----------
    def closeEvent(self, event) -> None:
        if self.worker.is_busy:
            box = MessageBox(
                "退出软件",
                "有任务正在处理，退出将停止当前任务。确定退出吗？",
                self,
            )
            if not box.exec():
                event.ignore()
                return
        self.worker.stop()
        self.worker.wait(10000)
        event.accept()
