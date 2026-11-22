"""磁盘空间预检：开始处理前估算临时空间与输出体积。"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .engines import MediaInfo
from .i18n import t

# PNG 帧大小与画面复杂度有关；实测约 0.2-0.6 字节/像素，
# 这里取 1.0 字节/像素并额外留 15% 余量，偏保守以避免中途写满磁盘。
BYTES_PER_PIXEL = 1.0
SAFETY_FACTOR = 1.15
TEMP_RESERVE = 256 * 1024**2
OUTPUT_RESERVE = 64 * 1024**2
# H.264 CRF 18 的粗略码率估算：约 0.12 bit/像素/帧。
# 用目标像素率估算，避免按源文件体积线性放大导致超大源文件被误判。
OUTPUT_BITS_PER_PIXEL = 0.12


def format_size(num: float) -> str:
    if num >= 1024**4:
        return f"{num / 1024**4:.1f} TB"
    if num >= 1024**3:
        return f"{num / 1024**3:.1f} GB"
    if num >= 1024**2:
        return f"{num / 1024**2:.0f} MB"
    return f"{max(1, int(round(num / 1024)))} KB"


def estimate_temp_bytes(
    info: MediaInfo,
    sr_plan: dict | None,
    fi_passes: int,
    keep_temp: bool = False,
) -> int:
    """估算工作目录峰值占用（帧会随阶段完成及时删除）。"""
    if info.duration <= 0 or info.fps <= 0:
        return TEMP_RESERVE
    frames = max(1, int(round(info.duration * info.fps)))
    source_px = max(1, info.width * info.height)

    sr_px = source_px
    if sr_plan is not None and not sr_plan.get("skip"):
        scale = max(1, int(sr_plan.get("scale", 1)))
        sr_px = source_px * scale * scale

    dirs = [frames * source_px]  # 抽帧
    if sr_plan is not None and not sr_plan.get("skip"):
        dirs.append(frames * sr_px)  # 超分
    current = frames * sr_px
    for _ in range(max(0, int(fi_passes))):
        current *= 2
        dirs.append(current)  # 每一遍补帧

    if keep_temp or len(dirs) == 1:
        peak = sum(dirs)
    else:
        peak = max(dirs[index] + dirs[index + 1] for index in range(len(dirs) - 1))
    return int(peak * BYTES_PER_PIXEL * SAFETY_FACTOR + TEMP_RESERVE)


def estimate_output_bytes(
    info: MediaInfo,
    final_w: int,
    final_h: int,
    final_fps: float,
    source_bytes: int | None = None,
) -> int:
    """按目标像素率与源文件体积估算输出体积。

    不按源文件体积乘像素/帧率比例：蓝光原盘等超高码率源会被放大到
    数百 GB，造成误判。改为按目标分辨率/帧率估算，并至少预留源文件
    同等空间。
    """
    if source_bytes is None:
        source_bytes = paths.file_size(info.path)
    estimated = 0.0
    if info.duration > 0:
        pixels_per_second = (
            max(1, final_w) * max(1, final_h) * max(0.1, final_fps)
        )
        estimated = (
            info.duration
            * pixels_per_second
            * OUTPUT_BITS_PER_PIXEL
            / 8.0
        )
    return int(max(float(source_bytes), estimated) + OUTPUT_RESERVE)


@dataclass
class DiskSpaceIssue:
    kind: str  # temp / output / both
    path: Path
    required: int
    available: int

    def message(self) -> str:
        if self.kind == "both":
            return t(
                "临时目录和输出位置所在的磁盘空间不足："
                "需要约 {need}，当前可用 {free}。\n位置：{path}",
                need=format_size(self.required),
                free=format_size(self.available),
                path=self.path,
            )
        if self.kind == "temp":
            return t(
                "临时空间不足：需要约 {need}，当前可用 {free}。\n位置：{path}",
                need=format_size(self.required),
                free=format_size(self.available),
                path=self.path,
            )
        return t(
            "输出位置空间不足：需要约 {need}，当前可用 {free}。\n位置：{path}",
            need=format_size(self.required),
            free=format_size(self.available),
            path=self.path,
        )


def _drive(path: Path) -> str:
    return os.path.splitdrive(os.path.abspath(str(path)))[0].lower()


def free_bytes(path: Path) -> int | None:
    """磁盘可用字节数；无法判断时返回 None。"""
    return _free_bytes(path)


def _free_bytes(path: Path) -> int | None:
    candidate = Path(path)
    while True:
        try:
            if candidate.exists():
                break
        except OSError:
            pass
        if candidate.parent == candidate:
            return None
        candidate = candidate.parent
    try:
        return shutil.disk_usage(str(candidate)).free
    except OSError:
        return None


def check_disk_space(
    temp_dir: Path,
    temp_required: int,
    output_dir: Path,
    output_required: int,
) -> list[DiskSpaceIssue]:
    """检查临时目录与输出目录所在磁盘；同一磁盘会合并需求。"""
    entries: list[tuple[str, Path, int]] = []
    if temp_required > 0:
        entries.append(("temp", Path(temp_dir), temp_required))
    if output_required > 0:
        entries.append(("output", Path(output_dir), output_required))
    if not entries:
        return []

    grouped: dict[str, dict] = {}
    for kind, path, required in entries:
        drive = _drive(path)
        group = grouped.setdefault(
            drive, {"kinds": [], "paths": [], "required": 0}
        )
        group["kinds"].append(kind)
        group["paths"].append(path)
        group["required"] += required

    issues: list[DiskSpaceIssue] = []
    for group in grouped.values():
        available = _free_bytes(group["paths"][0])
        if available is None:
            continue
        if available < group["required"]:
            kind = "both" if len(set(group["kinds"])) > 1 else group["kinds"][0]
            issues.append(
                DiskSpaceIssue(
                    kind=kind,
                    path=group["paths"][0],
                    required=group["required"],
                    available=available,
                )
            )
    return issues


def ensure_writable(directory: Path) -> None:
    """确认目录存在且可写；不可写时抛出 OSError。"""
    paths.write_probe(directory)
