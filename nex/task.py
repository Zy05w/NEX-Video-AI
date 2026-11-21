"""任务模型与状态定义。"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from .i18n import t


class TaskStatus(str, Enum):
    PENDING = "等待中"
    RUNNING = "处理中"
    DONE = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"


ACTIVE_STATUSES = (TaskStatus.PENDING, TaskStatus.RUNNING)


@dataclass
class TaskParams:
    input_path: str
    output_dir: str = ""
    sr_enabled: bool = True
    sr_model: str = "realesr-animevideov3"
    sr_scale: int | None = 2
    sr_height: int | None = None
    fi_enabled: bool = True
    fi_model: str = "rife-v4.6"
    fi_mult: int | None = 2
    fi_fps: float | None = None
    encoder: str = "auto"
    crf: int = 18
    preset: str = "medium"
    gpu_id: int = 0
    temp_limit: float = 88.0
    keep_temp: bool = False

    def summary(self) -> str:
        if self.sr_enabled:
            if self.sr_height:
                names = {1080: "1080p", 1440: "2K", 2160: "4K"}
                sr = names.get(self.sr_height, f"{self.sr_height}p")
            elif self.sr_scale:
                sr = f"{self.sr_scale}x"
            else:
                sr = t("超分")
        else:
            sr = t("不超分")
        if self.fi_enabled:
            if self.fi_mult:
                fi = f"{self.fi_mult}x"
            elif self.fi_fps:
                fi = f"{self.fi_fps:g}fps"
            else:
                fi = t("补帧")
        else:
            fi = t("不补帧")
        return f"{sr} / {fi}"


@dataclass
class Task:
    id: str
    file_name: str
    params: TaskParams
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    stage: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    output_path: str = ""
    error: str = ""
    log_path: str = ""

    @property
    def status_text(self) -> str:
        return self.status.value

    @property
    def summary(self) -> str:
        return self.params.summary()

    def to_data_json(self) -> str:
        return json.dumps(
            {"file_name": self.file_name, "params": asdict(self.params)},
            ensure_ascii=False,
        )

    @classmethod
    def from_data_json(cls, data: str) -> tuple[str, TaskParams]:
        payload = json.loads(data)
        params = TaskParams(**payload.get("params", {}))
        return payload.get("file_name", ""), params


def new_task(params: TaskParams) -> Task:
    return Task(
        id=uuid.uuid4().hex[:12],
        file_name=Path(params.input_path).name,
        params=params,
    )
