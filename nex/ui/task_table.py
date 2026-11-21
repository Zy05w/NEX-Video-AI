"""任务列表表格（S2：演示数据）。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
)
from qfluentwidgets import CaptionLabel, ProgressBar, PushButton, TableWidget

STATUS_PENDING = "等待中"
STATUS_RUNNING = "处理中"
STATUS_DONE = "已完成"
STATUS_FAILED = "失败"
STATUS_CANCELLED = "已取消"

STATUS_COLORS = {
    STATUS_PENDING: "#6B7280",
    STATUS_RUNNING: "#4A9EFF",
    STATUS_DONE: "#2FB344",
    STATUS_FAILED: "#E5484D",
    STATUS_CANCELLED: "#9CA3AF",
}


@dataclass
class TaskRow:
    file_name: str
    file_path: str = ""
    status: str = STATUS_PENDING
    progress: int = 0
    summary: str = ""
    logs: list[str] = field(default_factory=list)
    bar: object = field(default=None, repr=False)
    label: object = field(default=None, repr=False)


class TaskTableWidget(TableWidget):
    """任务表格：文件名 / 状态 / 进度 / 目标参数 / 操作。"""

    logMessage = Signal(object, str)
    taskSelected = Signal(object)
    deleteRequested = Signal(int)

    HEADERS = ["文件名", "状态", "进度", "目标参数", "操作"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: list[TaskRow] = []
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().hide()
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setColumnWidth(1, 90)
        self.setColumnWidth(2, 200)
        self.setColumnWidth(4, 170)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    # ---------- 对外接口 ----------
    def add_task(self, task: TaskRow) -> None:
        row = len(self._tasks)
        self._tasks.append(task)
        self.insertRow(row)
        self.setRowHeight(row, 48)

        name_item = QTableWidgetItem(task.file_name)
        name_item.setToolTip(task.file_path or task.file_name)
        self.setItem(row, 0, name_item)

        status_item = QTableWidgetItem(task.status)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(STATUS_COLORS.get(task.status, "#1F2329")))
        self.setItem(row, 1, status_item)

        self.setCellWidget(row, 2, self._build_progress(task))

        summary_item = QTableWidgetItem(task.summary or "—")
        summary_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 3, summary_item)

        self.setCellWidget(row, 4, self._build_actions(task))

    def remove_task(self, index: int) -> None:
        if 0 <= index < len(self._tasks):
            self._tasks.pop(index)
            self.removeRow(index)

    def current_task(self) -> TaskRow | None:
        row = self.currentRow()
        if 0 <= row < len(self._tasks):
            return self._tasks[row]
        return None

    def task_at(self, index: int) -> TaskRow | None:
        if 0 <= index < len(self._tasks):
            return self._tasks[index]
        return None

    def start_all(self) -> int:
        """演示：把所有等待/失败/取消的任务标记为处理中。"""
        count = 0
        for task in self._tasks:
            if task.status in (STATUS_PENDING, STATUS_FAILED, STATUS_CANCELLED):
                task.status = STATUS_RUNNING
                task.progress = 5
                self._refresh_row(self._index_of(task))
                task.logs.append(f"{_now()} [开始] 开始处理（演示数据）")
                count += 1
        return count

    def advance_demo_progress(self) -> None:
        for task in list(self._tasks):
            if task.status != STATUS_RUNNING:
                continue
            task.progress = min(100, task.progress + random.randint(1, 3))
            self._refresh_progress(self._index_of(task))
            if task.progress >= 100:
                task.status = STATUS_DONE
                self._refresh_row(self._index_of(task))
                self._emit_log(task, "[完成] 处理完成（演示数据）")

    # ---------- 内部 ----------
    def _index_of(self, task: TaskRow) -> int:
        return self._tasks.index(task)

    def _build_progress(self, task: TaskRow) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        bar = ProgressBar(widget, useAni=False)
        bar.setValue(task.progress)
        bar.setFixedHeight(8)
        label = CaptionLabel(f"{task.progress}%", widget)
        label.setFixedWidth(38)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(bar, 1)
        layout.addWidget(label)
        task.bar = bar
        task.label = label
        return widget

    def _build_actions(self, task: TaskRow) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        if task.status in (STATUS_PENDING, STATUS_RUNNING):
            cancel_btn = PushButton(widget)
            cancel_btn.setText("取消")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(lambda _=False, t=task: self._cancel(t))
            layout.addWidget(cancel_btn)
        elif task.status in (STATUS_FAILED, STATUS_CANCELLED):
            retry_btn = PushButton(widget)
            retry_btn.setText("重试")
            retry_btn.setFixedHeight(28)
            retry_btn.clicked.connect(lambda _=False, t=task: self._retry(t))
            layout.addWidget(retry_btn)

        delete_btn = PushButton(widget)
        delete_btn.setText("删除")
        delete_btn.setFixedHeight(28)
        delete_btn.clicked.connect(
            lambda _=False, t=task: self.deleteRequested.emit(self._index_of(t))
        )
        layout.addWidget(delete_btn)
        layout.addStretch(1)
        return widget

    def _refresh_row(self, row: int) -> None:
        if not (0 <= row < len(self._tasks)):
            return
        task = self._tasks[row]
        status_item = self.item(row, 1)
        if status_item:
            status_item.setText(task.status)
            status_item.setForeground(QColor(STATUS_COLORS.get(task.status, "#1F2329")))
        self._refresh_progress(row)
        old = self.cellWidget(row, 4)
        self.setCellWidget(row, 4, self._build_actions(task))
        if old:
            old.deleteLater()

    def _refresh_progress(self, row: int) -> None:
        task = self._tasks[row]
        if task.bar is not None:
            task.bar.setValue(task.progress)
        if task.label is not None:
            task.label.setText(f"{task.progress}%")

    def _cancel(self, task: TaskRow) -> None:
        if task.status not in (STATUS_PENDING, STATUS_RUNNING):
            return
        task.status = STATUS_CANCELLED
        self._refresh_row(self._index_of(task))
        self._emit_log(task, "[取消] 任务已取消（演示数据）")

    def _retry(self, task: TaskRow) -> None:
        task.status = STATUS_PENDING
        task.progress = 0
        self._refresh_row(self._index_of(task))
        self._emit_log(task, "[重试] 已重新加入队列（演示数据）")

    def _emit_log(self, task: TaskRow, message: str) -> None:
        line = f"{_now()} {message}"
        task.logs.append(line)
        self.logMessage.emit(task, line)

    def _on_selection_changed(self) -> None:
        task = self.current_task()
        if task is not None:
            self.taskSelected.emit(task)


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")
