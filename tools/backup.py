"""项目本地备份：生成带日期的 zip（包含 .git 历史，排除引擎/虚拟环境）。"""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT.parent / "NEX-backups"

EXCLUDE_PARTS = {
    ".venv",
    ".venv-rife",
    "wheels",
    "engines",
    ".test",
    ".pytest_cache",
    "Real-ESRGAN-main",
    "Practical-RIFE",
    "__pycache__",
    "dist",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def main() -> int:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = BACKUP_DIR / f"NEX_{stamp}.zip"

    count = 0
    with zipfile.ZipFile(
        target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in EXCLUDE_PARTS for part in rel.parts):
                continue
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            archive.write(path, rel)
            count += 1

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"备份完成：{target}")
    print(f"文件数：{count} · 大小：{size_mb:.2f} MB")
    print("说明：引擎与模型、虚拟环境、测试产物不在备份内。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
