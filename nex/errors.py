"""把系统与引擎错误转成普通用户能看懂的提示。"""

from __future__ import annotations

from pathlib import Path

from .i18n import t

_DISK_FULL = {28, 112}
_NOT_FOUND = {2, 3}
_ACCESS_DENIED = {5}
_PATH_TOO_LONG = {206}
_IN_USE = {32, 33}


def _code(exc: OSError) -> int | None:
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int):
        return winerror
    return exc.errno


def friendly_os_error(exc: OSError, path: str | Path | None = None) -> str:
    """把 OSError 转成中文说明，保留原始信息便于排查。"""
    code = _code(exc)
    target = str(path) if path is not None else ""
    if code in _DISK_FULL:
        return t(
            "磁盘空间不足：{path}。请清理磁盘空间后重试。", path=target
        )
    if code in _NOT_FOUND:
        return t("找不到文件或文件夹：{path}。", path=target)
    if code in _ACCESS_DENIED:
        return t(
            "没有权限访问：{path}。请换一个输出位置，或以管理员身份运行软件。",
            path=target,
        )
    if code in _PATH_TOO_LONG:
        return t(
            "路径过长，Windows 无法处理：{path}。"
            "请把视频或输出位置移到路径更短的文件夹。",
            path=target,
        )
    if code in _IN_USE:
        return t(
            "文件正被其他程序占用：{path}。请关闭占用该文件的程序后重试。",
            path=target,
        )
    return t(
        "文件或文件夹操作失败：{message}", message=str(exc)
    )


def diagnose_engine_log(text: str) -> str | None:
    """从 FFmpeg / 引擎输出中识别常见错误，返回友好提示。"""
    lower = (text or "").lower()
    if not lower:
        return None
    if (
        "no space left on device" in lower
        or "not enough space" in lower
        or "disk full" in lower
    ):
        return t("磁盘空间不足，处理无法继续。请清理磁盘空间后重试。")
    if "permission denied" in lower or "access is denied" in lower:
        return t("没有权限写入文件或文件夹。请换一个输出位置后重试。")
    if (
        "filename or extension is too long" in lower
        or "path too long" in lower
        or "filename too long" in lower
    ):
        return t(
            "文件路径过长，系统无法处理。"
            "请把视频和输出位置移到路径更短的文件夹。"
        )
    if "no such file or directory" in lower:
        return t("找不到视频文件或相关文件。")
    if (
        "moov atom not found" in lower
        or "invalid data found" in lower
        or "error opening input" in lower
        or "could not find codec parameters" in lower
    ):
        return t("无法读取视频文件，文件可能已损坏或格式不受支持。")
    return None
