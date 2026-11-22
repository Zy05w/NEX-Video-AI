"""路径与资源定位（含 Windows 超长路径支持）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows 对普通路径的默认上限是 260 个字符；超过时使用 \\?\ 前缀
# 可以让 Python 与外部引擎（FFmpeg 等）绕过该限制。
_LONG_PATH_THRESHOLD = 248


def resource_path(name: str) -> Path:
    """返回打包后 / 开发时的资源文件路径。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "nex" / "resources" / name


def extended_path(path: str | Path) -> str:
    """返回适合 Windows 超长路径的路径字符串。

    短路径原样返回，避免影响普通文件与第三方程序；
    长路径转为绝对路径并加 ``\\\\?\\``（UNC 路径用 ``\\\\?\\UNC\\``）。
    """
    raw = os.fspath(path)
    if os.name != "nt" or raw.startswith("\\\\?\\"):
        return raw
    absolute = os.path.abspath(raw)
    if len(absolute) < _LONG_PATH_THRESHOLD:
        return raw
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


# 供外部进程使用的别名，语义更明确
external_path = extended_path


def exists(path: str | Path) -> bool:
    raw = os.fspath(path)
    try:
        if os.path.exists(raw):
            return True
    except (OSError, ValueError):
        pass
    candidate = extended_path(raw)
    if candidate == raw:
        return False
    try:
        return os.path.exists(candidate)
    except (OSError, ValueError):
        return False


def is_file(path: str | Path) -> bool:
    raw = os.fspath(path)
    try:
        if os.path.isfile(raw):
            return True
    except (OSError, ValueError):
        pass
    candidate = extended_path(raw)
    if candidate == raw:
        return False
    try:
        return os.path.isfile(candidate)
    except (OSError, ValueError):
        return False


def file_size(path: str | Path) -> int:
    raw = os.fspath(path)
    for candidate in (raw, extended_path(raw)):
        try:
            return os.stat(candidate).st_size
        except (OSError, ValueError):
            continue
    return 0


def makedirs(path: str | Path, exist_ok: bool = True) -> None:
    raw = os.fspath(path)
    try:
        os.makedirs(raw, exist_ok=exist_ok)
        return
    except OSError:
        candidate = extended_path(raw)
        if candidate == raw:
            raise
    os.makedirs(candidate, exist_ok=exist_ok)


def write_probe(directory: str | Path) -> None:
    """在目录内写入并删除一个很小的探针文件，用于检查写权限。"""
    makedirs(directory)
    probe = Path(directory) / ".nex_write_test"
    raw = os.fspath(probe)
    target = extended_path(raw)
    with open(target, "wb") as handle:
        handle.write(b"nex")
    os.remove(target)
