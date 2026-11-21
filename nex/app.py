"""应用入口：初始化 Qt、主题与主窗口。"""

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import QApplication

from . import APP_NAME, APP_VERSION
from .app_config import AppConfig
from .i18n import set_language, t
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def restart_app() -> None:
    """以当前语言设置重新启动应用。"""
    if getattr(sys, "frozen", False):
        program, args = sys.executable, []
    else:
        program, args = sys.executable, ["-m", "nex"]
    QProcess.startDetached(program, args, str(Path.cwd()))
    app = QApplication.instance()
    if app is not None:
        app.quit()


def main() -> None:
    app = QApplication(sys.argv)
    config = AppConfig.load()
    set_language(config.language)
    app.setApplicationName(t(APP_NAME))
    app.setApplicationDisplayName(t(APP_NAME))
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("NEX")

    apply_theme(app)

    window = MainWindow(config=config)
    window.show()

    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        QTimer.singleShot(1500, app.quit)

    code = app.exec()
    if smoke_test:
        print("SMOKE_TEST_OK")
    raise SystemExit(code)
