"""拖入视频测试入口（S3 临时工具，S5 后由主界面取代）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

OPTIONS = {
    "1": (
        "动漫：超分 2x + 补帧 2x",
        ["--sr", "realesr-animevideov3", "--sr-scale", "2",
         "--fi", "rife-v4.6", "--fi-mult", "2"],
    ),
    "2": (
        "真人：超分 2x + 补帧 2x",
        ["--sr", "realesrgan-x4plus", "--sr-scale", "2",
         "--fi", "rife-v4.6", "--fi-mult", "2"],
    ),
    "3": (
        "只超分 2x（动漫模型）",
        ["--sr", "realesr-animevideov3", "--sr-scale", "2"],
    ),
    "4": (
        "只补帧 2x",
        ["--fi", "rife-v4.6", "--fi-mult", "2"],
    ),
}


def pick_file() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # tkinter 不可用时的兜底
        print(f"无法打开文件选择窗口：{exc}")
        print("请把视频文件拖到本文件图标上运行。")
        return ""
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    path = filedialog.askopenfilename(
        title="选择要处理的视频",
        filetypes=[
            ("视频文件", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v"),
            ("所有文件", "*.*"),
        ],
    )
    root.destroy()
    return path


def choose() -> str:
    print("请选择处理方式：")
    for key, (label, _) in OPTIONS.items():
        print(f"  {key} = {label}")
    while True:
        try:
            choice = input("输入 1-4（直接回车默认 1）：").strip() or "1"
        except EOFError:
            return "1"
        if choice in OPTIONS:
            return choice
        print("输入无效，请重新输入。")


def main() -> int:
    if not PYTHON.exists():
        print(f"找不到运行环境：{PYTHON}")
        print("请确认项目文件夹完整（.venv 目录存在）。")
        return 1

    video = sys.argv[1] if len(sys.argv) > 1 else ""
    if video:
        print(f"已选择：{video}")
    else:
        print("未检测到拖入的视频，正在打开文件选择窗口...")
        video = pick_file()
    if not video:
        print("未选择视频，已退出。")
        return 1

    video_path = Path(video)
    if not video_path.exists():
        print(f"文件不存在：{video_path}")
        return 1

    choice = choose()
    label, args = OPTIONS[choice]
    print(f"\n开始处理：{label}")
    print("处理过程中可随时按 Ctrl+C 取消。\n")
    sys.stdout.flush()

    try:
        code = subprocess.call(
            [str(PYTHON), "-m", "nex.cli", str(video_path), *args],
            cwd=str(ROOT),
        )
    except KeyboardInterrupt:
        code = 130
    if code == 0:
        print("\n处理完成，输出文件在原视频同目录（文件名带 _NEX 后缀）。")
    elif code == 130:
        print("\n已取消。")
    else:
        print(f"\n处理结束（退出码 {code}），请查看上方日志路径。")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
