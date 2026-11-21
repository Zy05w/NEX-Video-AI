"""主窗口（S2：界面骨架 + 演示数据）。"""

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import QTimer
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
from ..app_config import AppConfig
from .add_task_dialog import AddTaskDialog, NewTaskRequest
from .settings_dialog import SettingsDialog
from .task_table import (
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TaskRow,
    TaskTableWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 760)
        self.setMinimumSize(960, 600)
        self._build_ui()
        self._load_demo_tasks()

        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self.table.advance_demo_progress)
        self._demo_timer.start(700)

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
        self.table.logMessage.connect(self._on_task_log)
        self.table.taskSelected.connect(self._on_task_selected)
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
        clear_btn.clicked.connect(self.logEdit_clear)
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

        self.statusBar().showMessage("演示模式（S2）：界面骨架，尚未接入真实 AI 处理")

    def _load_demo_tasks(self) -> None:
        now = _now()
        demos = [
            TaskRow(
                file_name="动漫01.mp4",
                file_path=r"D:\Videos\动漫01.mp4",
                status=STATUS_RUNNING,
                progress=45,
                summary="4K / 60fps",
                logs=[
                    f"{now} [探测] 1920×1080 · 23.98fps · 时长 24:00（演示）",
                    f"{now} [抽帧] 完成，共 480 帧（演示）",
                    f"{now} [超分] 120/480 帧（25%）（演示）",
                ],
            ),
            TaskRow(
                file_name="旅拍.mp4",
                file_path=r"D:\Videos\旅拍.mp4",
                status=STATUS_PENDING,
                progress=0,
                summary="2x / 60fps",
                logs=[f"{now} [等待] 已加入任务队列（演示）"],
            ),
            TaskRow(
                file_name="电影.mp4",
                file_path=r"D:\Videos\电影.mp4",
                status=STATUS_DONE,
                progress=100,
                summary="4K / 不补帧",
                logs=[
                    f"{now} [合成] 输出完成：电影_4K.mp4（演示）",
                    f"{now} [完成] 耗时 18 分 32 秒（演示）",
                ],
            ),
            TaskRow(
                file_name="旧番.mp4",
                file_path=r"D:\Videos\旧番.mp4",
                status=STATUS_FAILED,
                progress=25,
                summary="2x / 2x",
                logs=[f"{now} [错误] 引擎退出码 1：显存不足（演示）"],
            ),
            TaskRow(
                file_name="演唱会.mp4",
                file_path=r"D:\Videos\演唱会.mp4",
                status=STATUS_CANCELLED,
                progress=10,
                summary="4K / 120fps",
                logs=[f"{now} [取消] 任务已取消（演示）"],
            ),
        ]
        for task in demos:
            self.table.add_task(task)
        self.table.selectRow(0)

    # ---------- 事件 ----------
    def _on_task_selected(self, task) -> None:
        if task is None:
            self.logTitle.setText("日志 · 未选择任务")
            self.logEdit.clear()
            return
        self.logTitle.setText(f"日志 · {task.file_name}")
        self.logEdit.clear()
        for line in task.logs[-300:]:
            self.logEdit.append(line)

    def _on_task_log(self, task, line: str) -> None:
        if self.table.current_task() is task:
            self.logEdit.append(line)

    def logEdit_clear(self) -> None:
        self.logEdit.clear()

    def _on_add_task(self) -> None:
        dialog = AddTaskDialog(self)
        if not dialog.exec() or dialog.request is None:
            return
        request = dialog.request
        summary = self._summary(request)
        for path in request.files:
            task = TaskRow(
                file_name=os.path.basename(path),
                file_path=path,
                status=STATUS_RUNNING if request.start_now else STATUS_PENDING,
                progress=5 if request.start_now else 0,
                summary=summary,
                logs=[],
            )
            task.logs.append(f"{_now()} [添加] 已加入任务队列（演示数据）")
            if request.start_now:
                task.logs.append(f"{_now()} [开始] 开始处理（演示数据）")
            self.table.add_task(task)
        self.table.selectRow(self.table.rowCount() - 1)
        self.statusBar().showMessage(
            f"已添加 {len(request.files)} 个任务（演示数据）", 4000
        )

    def _on_start_all(self) -> None:
        count = self.table.start_all()
        if count:
            self.statusBar().showMessage(f"已开始 {count} 个任务（演示数据）", 4000)
        else:
            self.statusBar().showMessage("没有可开始的任务", 3000)
        current = self.table.current_task()
        if current is not None:
            self._on_task_selected(current)

    def _on_settings(self) -> None:
        SettingsDialog(self.config, self).exec()

    def _on_delete_requested(self, index: int) -> None:
        task = self.table.task_at(index)
        if task is None:
            return
        box = MessageBox(
            "删除任务记录",
            f"确定删除「{task.file_name}」的记录吗？\n仅删除记录，不会删除视频文件。",
            self,
        )
        if box.exec():
            self.table.remove_task(index)
            if self.table.rowCount() == 0:
                self._on_task_selected(None)
            else:
                self.table.selectRow(min(index, self.table.rowCount() - 1))

    # ---------- 工具 ----------
    @staticmethod
    def _summary(request: NewTaskRequest) -> str:
        if request.sr_enabled:
            sr = "超分" if request.resolution == "原始" else request.resolution
        else:
            sr = "不超分"
        if request.fi_enabled:
            if request.fps in ("2x", "4x"):
                fi = request.fps
            elif request.fps == "原始":
                fi = "补帧"
            else:
                fi = f"{request.fps}fps"
        else:
            fi = "不补帧"
        return f"{sr} / {fi}"


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")
