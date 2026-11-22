"""通用小控件。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox


def make_spin_box(
    parent=None,
    minimum: int = 0,
    maximum: int = 100,
    value: int = 0,
    width: int = 140,
) -> QSpinBox:
    box = QSpinBox(parent)
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setFixedWidth(width)
    box.setAlignment(Qt.AlignCenter)
    return box
