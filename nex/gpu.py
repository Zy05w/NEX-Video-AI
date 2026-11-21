"""NVIDIA GPU 状态查询与温度保护。"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .logger import TaskLogger

CREATE_NO_WINDOW = 0x08000000


@dataclass
class GpuStatus:
    name: str
    temperature: int | None
    utilization: int | None
    memory_used: int | None
    power: float | None


def _to_int(value: str) -> int | None:
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return None


def _to_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def parse_gpu_line(line: str) -> GpuStatus | None:
    parts = [part.strip() for part in (line or "").strip().split(",")]
    if len(parts) < 5:
        return None
    return GpuStatus(
        name=parts[0],
        temperature=_to_int(parts[1]),
        utilization=_to_int(parts[2]),
        memory_used=_to_int(parts[3]),
        power=_to_float(parts[4]),
    )


def query_gpu() -> Optional[GpuStatus]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,power.draw",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return None
    return parse_gpu_line(lines[0])


class GpuMonitor(threading.Thread):
    """后台采样 GPU 温度；超过上限时触发取消。

    NVIDIA 笔记本 GPU 的目标温度（降频点）约 87°C，固件本身有保护；
    本监控是额外的软件兜底，默认上限 88°C。
    """

    def __init__(
        self,
        logger: TaskLogger,
        cancel_event: threading.Event,
        limit: float = 88.0,
        interval: float = 5.0,
    ):
        super().__init__(daemon=True, name="gpu-monitor")
        self.logger = logger
        self.cancel_event = cancel_event
        self.limit = float(limit)
        self.interval = max(1.0, float(interval))
        self.overheated = False
        self.max_temp: int | None = None
        self.last: GpuStatus | None = None
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.wait(self.interval):
            status = query_gpu()
            if status is None:
                continue
            self.last = status
            if status.temperature is None:
                continue
            self.max_temp = (
                status.temperature
                if self.max_temp is None
                else max(self.max_temp, status.temperature)
            )
            self.logger.log(
                "温度",
                f"GPU {status.temperature}°C · 占用 {status.utilization}% · "
                f"功耗 {status.power}W · 显存 {status.memory_used}MiB",
            )
            if status.temperature >= self.limit:
                self.overheated = True
                self.logger.log(
                    "温度",
                    f"温度达到 {status.temperature}°C（保护上限 "
                    f"{self.limit:g}°C），正在安全停止任务",
                )
                self.cancel_event.set()
                return

    def stop(self) -> None:
        self._stop_event.set()
