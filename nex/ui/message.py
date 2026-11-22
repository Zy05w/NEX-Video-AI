"""确认框与提示框（原生 Qt 样式）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ..i18n import t
from .base_dialog import BaseDialog


class MessageDialog(BaseDialog):
    def __init__(
        self,
        parent,
        title: str,
        text: str,
        ok_text: str | None = None,
        cancel_text: str | None = None,
        show_cancel: bool = True,
    ):
        super().__init__(title, parent, show_cancel=show_cancel)
        label = QLabel(text, self)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setMinimumWidth(420)
        self.contentLayout.addWidget(label)
        self.okButton.setText(ok_text or t("确定"))
        if show_cancel:
            self.cancelButton.setText(cancel_text or t("取消"))


def ask(
    parent,
    title: str,
    text: str,
    ok_text: str | None = None,
    cancel_text: str | None = None,
) -> bool:
    dialog = MessageDialog(
        parent, title, text, ok_text=ok_text, cancel_text=cancel_text
    )
    return dialog.exec() == BaseDialog.Accepted


def notify(
    parent,
    title: str,
    text: str,
    ok_text: str | None = None,
) -> None:
    MessageDialog(
        parent,
        title,
        text,
        ok_text=ok_text,
        show_cancel=False,
    ).exec()
