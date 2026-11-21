"""应用入口：初始化 Qt、主题与主窗口。"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from . import APP_NAME, APP_VERSION
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("NEX")

    apply_theme(app)

    window = MainWindow()
    window.show()

    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        QTimer.singleShot(1500, app.quit)

    code = app.exec()
    if smoke_test:
        print("SMOKE_TEST_OK")
    raise SystemExit(code)
