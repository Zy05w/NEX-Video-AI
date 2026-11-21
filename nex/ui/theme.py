"""白色 + 淡蓝色主题（见 docs/03-界面设计规范.md）。"""

from PySide6.QtGui import QFont
from qfluentwidgets import Theme, setTheme, setThemeColor

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
QMainWindow { background: #FFFFFF; }
QWidget#centralWidget { background: #FFFFFF; }
QWidget#toolbar { background: #FFFFFF; }
QWidget#logPanel {
    background: #F5F9FF;
    border: 1px solid #E5EAF2;
    border-radius: 8px;
}
QStatusBar { background: #F5F9FF; color: #6B7280; }
QStatusBar::item { border: none; }
"""


def apply_theme(app) -> None:
    setTheme(Theme.LIGHT)
    setThemeColor(ACCENT)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setStyleSheet(APP_QSS)
