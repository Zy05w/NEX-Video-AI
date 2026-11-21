"""自定义控件与第三方组件兼容性修复。"""

from __future__ import annotations

from qfluentwidgets import SpinBox


def make_spin_box(
    parent=None,
    minimum: int = 0,
    maximum: int = 100,
    value: int = 0,
    width: int = 200,
) -> SpinBox:
    """创建可正常显示和输入的数字框。

    兼容性说明：qfluentwidgets 1.11.3 与当前 PySide6 组合下，SpinBox 内部的
    QLineEdit 会被布局压成 1px 宽，导致数值不可见、无法输入。这里通过设置
    内部输入框的最小宽度规避该问题。
    """
    box = SpinBox(parent)
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setFixedWidth(width)
    box.lineEdit().setMinimumWidth(max(80, width - 80))
    return box
