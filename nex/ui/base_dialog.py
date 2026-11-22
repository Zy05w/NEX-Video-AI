"""原生 Qt 对话框基类。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..i18n import t


class BaseDialog(QDialog):
    def __init__(self, title: str, parent=None, show_cancel: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("baseDialog")
        self.setMinimumWidth(620)
        self.setSizeGripEnabled(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.titleLabel = QLabel(title, self)
        self.titleLabel.setObjectName("dialogTitle")
        layout.addWidget(self.titleLabel)

        self.contentLayout = QVBoxLayout()
        self.contentLayout.setSpacing(12)
        layout.addLayout(self.contentLayout)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch(1)
        self.cancelButton = QPushButton(t("取消"), self)
        self.okButton = QPushButton(t("确定"), self)
        self.okButton.setObjectName("primaryButton")
        self.okButton.setDefault(True)
        self.cancelButton.clicked.connect(self.reject)
        self.okButton.clicked.connect(self.accept)
        button_row.addWidget(self.cancelButton)
        button_row.addWidget(self.okButton)
        layout.addLayout(button_row)

        if not show_cancel:
            self.cancelButton.hide()

    def set_ok_text(self, text: str) -> None:
        self.okButton.setText(text)

    def set_cancel_text(self, text: str) -> None:
        self.cancelButton.setText(text)
