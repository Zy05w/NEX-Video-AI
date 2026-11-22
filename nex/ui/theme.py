"""白色 + 淡蓝色主题（PySide6 原生控件 + QSS）。"""

import sys
from pathlib import Path

from PySide6.QtGui import QFont


def _resources_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "nex" / "resources"

ACCENT = "#4A9EFF"
ACCENT_HOVER = "#3A8EEF"
BG_PRIMARY = "#FFFFFF"
BG_SECONDARY = "#F5F9FF"
BG_ACCENT_SOFT = "#E8F2FF"
TEXT_PRIMARY = "#1F2329"
TEXT_SECONDARY = "#6B7280"
BORDER = "#E5EAF2"
SUCCESS = "#2FB344"
DANGER = "#E5484D"
WARNING = "#F5A623"

APP_QSS = """
QWidget {
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
    color: #1F2329;
}
QMainWindow, QDialog { background: #FFFFFF; }
QWidget#centralWidget, QWidget#toolbar { background: #FFFFFF; }

QLabel#titleLabel { font-size: 20px; font-weight: 600; }
QLabel#subtitleLabel { color: #6B7280; font-size: 12px; }
QLabel#dialogTitle { font-size: 20px; font-weight: 600; }
QLabel#errorLabel { color: #E5484D; }
QLabel#logTitle { font-size: 14px; font-weight: 600; }

QPushButton {
    background: #FFFFFF;
    border: 1px solid #DDE5F0;
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 20px;
    color: #1F2329;
}
QPushButton:hover { background: #F5F9FF; border-color: #BFD8FF; }
QPushButton:pressed { background: #E8F2FF; }
QPushButton:disabled { color: #9CA3AF; background: #F7F9FC; }
QPushButton#primaryButton {
    background: #4A9EFF;
    border: 1px solid #4A9EFF;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #3A8EEF; border-color: #3A8EEF; }
QPushButton#primaryButton:pressed { background: #2F7FDB; }
QPushButton#smallButton { padding: 2px 10px; min-height: 18px; font-size: 12px; }

QLineEdit, QComboBox, QSpinBox {
    background: #FFFFFF;
    border: 1px solid #DDE5F0;
    border-radius: 6px;
    padding: 5px 9px;
    min-height: 20px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #4A9EFF; }
QLineEdit:read-only { background: #FAFCFF; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down {
    width: 26px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    image: url("__ARROW_DOWN__");
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #DDE5F0;
    selection-background-color: #E8F2FF;
    selection-color: #1F2329;
    outline: none;
}
QSpinBox { padding-right: 24px; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 20px;
    border: none;
    background: transparent;
}
QSpinBox::up-arrow {
    image: url("__ARROW_UP__");
    width: 10px;
    height: 10px;
}
QSpinBox::down-arrow {
    image: url("__ARROW_DOWN__");
    width: 10px;
    height: 10px;
}

QCheckBox { spacing: 8px; color: #1F2329; }

QTableWidget {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 8px;
    gridline-color: #EEF2F8;
    selection-background-color: #E8F2FF;
    selection-color: #1F2329;
}
QTableWidget::item { padding: 4px; border: none; }
QHeaderView::section {
    background: #F5F9FF;
    color: #6B7280;
    border: none;
    border-bottom: 1px solid #E5EAF2;
    padding: 10px 8px;
    font-weight: 600;
}
QTableCornerButton::section { background: #F5F9FF; border: none; }

QProgressBar {
    background: #E9EFF7;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk { background: #4A9EFF; border-radius: 4px; }

QWidget#logPanel {
    background: #F5F9FF;
    border: 1px solid #E5EAF2;
    border-radius: 8px;
}
QTextEdit {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 6px;
    padding: 6px;
}
QStatusBar { background: #F5F9FF; color: #6B7280; }
QStatusBar::item { border: none; }

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #C9D6E8;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip {
    background: #FFFFFF;
    color: #1F2329;
    border: 1px solid #DDE5F0;
    padding: 4px 8px;
}
"""


def apply_theme(app) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    assets = _resources_dir()
    qss = (
        APP_QSS.replace(
            "__ARROW_DOWN__", (assets / "arrow_down.png").as_posix()
        ).replace("__ARROW_UP__", (assets / "arrow_up.png").as_posix())
    )
    app.setStyleSheet(qss)
