"""应用入口：初始化 Qt、主题与主窗口。"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import APP_NAME, APP_VERSION
from .app_config import AppConfig
from .i18n import set_language, t
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "nex" / "resources" / name


def _self_test() -> int:
    """打包后自检：检查引擎、模型与 GPU，并写入临时报告文件。"""
    from . import engines
    from .gpu import query_gpu

    lines = [f"NEX self-test {APP_VERSION}", f"app_root={engines.app_root()}"]
    problems: list[str] = []

    missing = engines.check_engines()
    if missing:
        problems.append("缺少引擎文件：\n" + "\n".join(missing))
    model_paths = [
        engines.realesrgan_dir() / "models" / "realesr-animevideov3-x2.bin",
        engines.realesrgan_dir() / "models" / "realesrgan-x4plus.bin",
        engines.rife_dir() / "rife-v4.6",
    ]
    for path in model_paths:
        if not path.exists():
            problems.append(f"缺少模型：{path}")

    try:
        proc = subprocess.run(
            [str(engines.ffmpeg_exe()), "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        first = (proc.stdout or "").strip().splitlines()
        lines.append("ffmpeg=" + (first[0] if first else "unknown"))
        if proc.returncode != 0:
            problems.append("ffmpeg 无法运行")
    except (OSError, subprocess.TimeoutExpired) as exc:
        problems.append(f"ffmpeg 启动失败：{exc}")

    status = query_gpu()
    if status is None:
        lines.append("gpu=nvidia-smi unavailable")
    else:
        lines.append(
            f"gpu={status.name} temp={status.temperature}°C "
            f"mem={status.memory_used}MiB"
        )

    lines.append("result=" + ("OK" if not problems else "FAIL"))
    lines.extend(problems)
    report = "\n".join(lines)
    try:
        (
            Path(tempfile.gettempdir()) / "NEX_selftest.txt"
        ).write_text(report, encoding="utf-8")
    except OSError:
        pass
    print(report)
    return 0 if not problems else 1


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
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())

    app = QApplication(sys.argv)
    config = AppConfig.load()
    set_language(config.language)
    app.setApplicationName(t(APP_NAME))
    app.setApplicationDisplayName(t(APP_NAME))
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("NEX")
    icon_path = resource_path("nex.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

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
