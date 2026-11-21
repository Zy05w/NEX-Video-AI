"""应用设置持久化（%APPDATA%/NEX/config.json）。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "NEX"


CONFIG_FILE = config_dir() / "config.json"


@dataclass
class AppConfig:
    output_dir: str = ""
    encoder: str = "auto"  # auto / x264 / nvenc
    gpu_id: int = 0
    log_keep_days: int = 30

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        if isinstance(data, dict):
            if isinstance(data.get("output_dir"), str):
                cfg.output_dir = data["output_dir"]
            if data.get("encoder") in ("auto", "x264", "nvenc"):
                cfg.encoder = data["encoder"]
            if isinstance(data.get("gpu_id"), int):
                cfg.gpu_id = data["gpu_id"]
            if isinstance(data.get("log_keep_days"), int):
                cfg.log_keep_days = max(1, min(365, data["log_keep_days"]))
        return cfg

    def save(self) -> None:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
