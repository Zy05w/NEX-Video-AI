"""任务列表表格（真实任务模型）。"""

from __future__ import annotations

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

from ..task import Task, TaskStatus

STATUS_COLORS = {
    TaskStatus.PENDING: "#6B7280",
    TaskStatus.RUNNING: "#4A9EFF",
    TaskStatus.DONE: "#2FB344",
    TaskStatus.FAILED: "#E5484D",
    TaskStatus.CANCELLED: "#9CA3AF",
}


class TaskTableWidget(TableWidget):
    """任务表格：文件名 / 状态 / 进度 / 目标参数 / 操作。"""

    taskSelected = Signal(object)
    cancelRequested = Signal(str)
    retryRequested = Signal(str)
    deleteRequested = Signal(str)

    HEADERS = ["文件名", "状态", "进度", "目标参数", "操作"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: list[Task] = []
        self._progress_widgets: dict[str, tuple[ProgressBar, CaptionLabel]] = {}
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
    def add_task(self, task: Task) -> None:
        row = len(self._tasks)
        self._tasks.append(task)
        self.insertRow(row)
        self.setRowHeight(row, 48)

        name_item = QTableWidgetItem(task.file_name)
        name_item.setToolTip(task.params.input_path)
        self.setItem(row, 0, name_item)

        status_item = QTableWidgetItem(task.status.value)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(STATUS_COLORS.get(task.status, "#1F2329")))
        self.setItem(row, 1, status_item)

        self.setCellWidget(row, 2, self._build_progress(task))

        summary_item = QTableWidgetItem(task.summary or "—")
        summary_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 3, summary_item)

        self.setCellWidget(row, 4, self._build_actions(task))

    def update_task(self, task: Task) -> None:
        for index, existing in enumerate(self._tasks):
            if existing.id == task.id:
                self._tasks[index] = task
                self._refresh_row(index)
                return

    def set_progress(self, task_id: str, percent: int, stage: str = "") -> None:
        task = self.task_by_id(task_id)
        if task is None:
            return
        task.progress = percent
        if stage:
            task.stage = stage
        widgets = self._progress_widgets.get(task_id)
        if widgets:
            bar, label = widgets
            bar.setValue(percent)
            label.setText(f"{percent}%")

    def remove_task(self, task_id: str) -> None:
        for index, task in enumerate(self._tasks):
            if task.id == task_id:
                self._tasks.pop(index)
                self._progress_widgets.pop(task_id, None)
                self.removeRow(index)
                return

    def task_by_id(self, task_id: str) -> Task | None:
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def current_task(self) -> Task | None:
        row = self.currentRow()
        if 0 <= row < len(self._tasks):
            return self._tasks[row]
        return None

    def task_at(self, index: int) -> Task | None:
        if 0 <= index < len(self._tasks):
            return self._tasks[index]
        return None

    # ---------- 内部 ----------
    def _build_progress(self, task: Task) -> QWidget:
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
        self._progress_widgets[task.id] = (bar, label)
        return widget

    def _build_actions(self, task: Task) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            cancel_btn = PushButton(widget)
            cancel_btn.setText("取消")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(
                lambda _=False, task_id=task.id: self.cancelRequested.emit(task_id)
            )
            layout.addWidget(cancel_btn)
        elif task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
            retry_btn = PushButton(widget)
            retry_btn.setText("重试")
            retry_btn.setFixedHeight(28)
            retry_btn.clicked.connect(
                lambda _=False, task_id=task.id: self.retryRequested.emit(task_id)
            )
            layout.addWidget(retry_btn)

        delete_btn = PushButton(widget)
        delete_btn.setText("删除")
        delete_btn.setFixedHeight(28)
        delete_btn.clicked.connect(
            lambda _=False, task_id=task.id: self.deleteRequested.emit(task_id)
        )
        layout.addWidget(delete_btn)
        layout.addStretch(1)
        return widget

    def _refresh_row(self, index: int) -> None:
        if not (0 <= index < len(self._tasks)):
            return
        task = self._tasks[index]
        status_item = self.item(index, 1)
        if status_item:
            status_item.setText(task.status.value)
            status_item.setForeground(
                QColor(STATUS_COLORS.get(task.status, "#1F2329"))
            )
        summary_item = self.item(index, 3)
        if summary_item:
            summary_item.setText(task.summary or "—")
        widgets = self._progress_widgets.get(task.id)
        if widgets:
            bar, label = widgets
            bar.setValue(task.progress)
            label.setText(f"{task.progress}%")
        old = self.cellWidget(index, 4)
        self.setCellWidget(index, 4, self._build_actions(task))
        if old:
            old.deleteLater()

    def _on_selection_changed(self) -> None:
        task = self.current_task()
        if task is not None:
            self.taskSelected.emit(task)
