"""主窗口：任务队列、处理控制与日志（原生 Qt）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from ..app_config import AppConfig, config_dir
from ..db import TaskRepository
from ..i18n import t
from ..logger import cleanup_old_logs
from ..pipeline import cleanup_stale_temp
from ..task import Task, TaskParams, TaskStatus, new_task
from ..worker import PipelineWorker
from .add_task_dialog import AddTaskDialog
from .message import ask, notify
from .settings_dialog import SettingsDialog
from .task_table import TaskTableWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        repo: TaskRepository | None = None,
        config: AppConfig | None = None,
    ):
        super().__init__()
        self.config = config if config is not None else AppConfig.load()
        self.repo = repo if repo is not None else TaskRepository()
        cleanup_stale_temp()
        cleanup_old_logs(self.config.log_keep_days)
        recovered = self.repo.recover_running()
        self._selected_task_id: str | None = None

        self.setWindowTitle(t(APP_NAME))
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
                t("已恢复 {count} 个未完成任务为等待中", count=recovered), 6000
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
        title = QLabel(t(APP_NAME), toolbar)
        title.setObjectName("titleLabel")
        subtitle = QLabel(t("AI 视频超分 · 补帧"), toolbar)
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        bar.addLayout(title_box)
        bar.addStretch(1)

        self.addBtn = QPushButton(t("添加任务"), toolbar)
        self.addBtn.setObjectName("primaryButton")
        self.addBtn.clicked.connect(self._on_add_task)

        self.startBtn = QPushButton(t("开始全部"), toolbar)
        self.startBtn.clicked.connect(self._on_start_all)

        self.settingsBtn = QPushButton(t("设置"), toolbar)
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
        self.table.detailsRequested.connect(self._on_details_requested)
        root.addWidget(self.table, 1)

        log_panel = QWidget(central)
        log_panel.setObjectName("logPanel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_layout.setSpacing(6)

        log_header = QHBoxLayout()
        self.logTitle = QLabel(t("日志 · 未选择任务"), log_panel)
        self.logTitle.setObjectName("logTitle")
        clear_btn = QPushButton(t("清空视图"), log_panel)
        clear_btn.setObjectName("smallButton")
        clear_btn.clicked.connect(self._clear_log_view)
        log_header.addWidget(self.logTitle)
        log_header.addStretch(1)
        log_header.addWidget(clear_btn)
        log_layout.addLayout(log_header)

        self.logEdit = QTextEdit(log_panel)
        self.logEdit.setReadOnly(True)
        self.logEdit.setMinimumHeight(140)
        self.logEdit.setMaximumHeight(180)
        self.logEdit.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.logEdit)
        root.addWidget(log_panel)

        self.statusBar().showMessage(t("就绪"))

    def _load_tasks(self) -> None:
        tasks = self.repo.list_all()
        for task in tasks:
            self.table.add_task(task)
        if tasks:
            self.table.selectRow(0)
            self._on_task_selected(tasks[0])
        self.statusBar().showMessage(
            t("就绪 · 共 {count} 个任务", count=len(tasks))
        )

    # ---------- 任务操作 ----------
    def _on_add_task(self) -> None:
        dialog = AddTaskDialog(self)
        if dialog.exec() != dialog.Accepted or dialog.request is None:
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
        self.statusBar().showMessage(
            t("已添加 {count} 个任务", count=len(added)), 4000
        )

    def _on_start_all(self) -> None:
        pending = self.repo.list_pending()
        for task in pending:
            self.worker.enqueue(task.id)
        if pending:
            self.statusBar().showMessage(
                t("已开始 {count} 个任务", count=len(pending)), 4000
            )
        else:
            self.statusBar().showMessage(t("没有等待中的任务"), 3000)

    def _on_cancel_requested(self, task_id: str) -> None:
        task = self.table.task_by_id(task_id)
        if task is None:
            return
        if task.status == TaskStatus.RUNNING:
            self.worker.cancel_task(task_id)
            self.statusBar().showMessage(t("正在取消任务..."), 3000)
        elif task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.stage = "已取消"
            self.repo.update(task)
            self.table.update_task(task)
            self.statusBar().showMessage(
                t("已取消：{name}", name=task.file_name), 4000
            )

    def _on_retry_requested(self, task_id: str) -> None:
        task = self.repo.get(task_id)
        if task is None or task.status not in (
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
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
        self.statusBar().showMessage(
            t("已重新加入队列：{name}", name=task.file_name), 4000
        )

    def _on_delete_requested(self, task_id: str) -> None:
        task = self.table.task_by_id(task_id)
        if task is None:
            return
        if task.status == TaskStatus.RUNNING:
            notify(
                self,
                t("无法删除"),
                t("任务正在处理中，请先取消后再删除。"),
            )
            return
        if ask(
            self,
            t("删除任务记录"),
            t(
                "确定删除「{name}」的记录吗？\n仅删除记录，不会删除视频文件。",
                name=task.file_name,
            ),
            ok_text=t("删除"),
        ):
            self.repo.delete(task_id)
            self.table.remove_task(task_id)
            if self._selected_task_id == task_id:
                self._selected_task_id = None
                self.logTitle.setText(t("日志 · 未选择任务"))
                self.logEdit.clear()
            self.statusBar().showMessage(t("已删除任务记录"), 3000)

    def _on_details_requested(self, task_id: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        log_path = task.log_path or str(
            config_dir() / "logs" / f"{task.id}.log"
        )
        notify(
            self,
            t("失败原因"),
            t(
                "「{name}」处理失败。\n\n{message}\n\n日志：{log}",
                name=task.file_name,
                message=(task.error or t("未知错误"))[:1200],
                log=log_path,
            ),
            ok_text=t("知道了"),
        )

    def _on_settings(self) -> None:
        old_language = self.config.language
        SettingsDialog(self.config, self).exec()
        if self.config.language == old_language:
            return
        if self.worker.is_busy:
            notify(
                self,
                t("语言已更改"),
                t("有任务正在处理，请在任务结束后手动重启软件使语言生效。"),
            )
            return
        if ask(
            self,
            t("语言已更改"),
            t("语言设置将在重启软件后生效。是否立即重启？"),
            ok_text=t("确定"),
        ):
            self.worker.stop()
            self.worker.wait(5000)
            from ..app import restart_app

            restart_app()

    # ---------- 工作线程信号 ----------
    def _on_task_started(self, task_id: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        self.table.update_task(task)
        self.statusBar().showMessage(
            t("正在处理：{name}", name=task.file_name)
        )
        if task_id == self._selected_task_id:
            self.logTitle.setText(t("日志 · {name}", name=task.file_name))

    def _on_task_progress(
        self, task_id: str, percent: int, stage: str, message: str
    ) -> None:
        self.table.set_progress(task_id, percent, stage)
        if task_id == self._selected_task_id:
            self.statusBar().showMessage(
                t(
                    "处理中：{stage} · {percent}%",
                    stage=t(stage),
                    percent=percent,
                )
            )

    def _on_task_log(self, task_id: str, line: str) -> None:
        if task_id == self._selected_task_id:
            self.logEdit.append(line)

    def _on_task_finished(self, task_id: str, outcome: str, message: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        self.table.update_task(task)
        if outcome == "done":
            text = t("已完成：{name}", name=task.file_name)
        elif outcome == "failed":
            text = t(
                "失败：{name} — {message}",
                name=task.file_name,
                message=message[:80],
            )
        else:
            text = t("已取消：{name}", name=task.file_name)
        self.statusBar().showMessage(text, 10000)
        if task_id == self._selected_task_id:
            self._show_task_log(task)

    # ---------- 日志 ----------
    def _on_task_selected(self, task: Task) -> None:
        self._selected_task_id = task.id
        latest = self.repo.get(task.id) or task
        self._show_task_log(latest)

    def _show_task_log(self, task: Task) -> None:
        self.logTitle.setText(t("日志 · {name}", name=task.file_name))
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
            lines = [f"[{t('错误')}] {task.error}"]
        if not lines:
            lines = [
                t("（暂无日志）目标参数：{summary}", summary=task.summary)
            ]
        for line in lines[-300:]:
            self.logEdit.append(line)

    def _clear_log_view(self) -> None:
        self.logEdit.clear()

    # ---------- 关闭 ----------
    def closeEvent(self, event) -> None:
        if self.worker.is_busy:
            if not ask(
                self,
                t("退出软件"),
                t("有任务正在处理，退出将停止当前任务。确定退出吗？"),
                ok_text=t("退出"),
            ):
                event.ignore()
                return
        self.worker.stop()
        self.worker.wait(10000)
        event.accept()
