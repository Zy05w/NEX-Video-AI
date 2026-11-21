"""第三方引擎封装：FFmpeg / Real-ESRGAN / RIFE。

实测要点（S1，见 docs/02）：
- 新版 FFmpeg 使用 -fps_mode passthrough（-vsync 已移除）。
- Real-ESRGAN / RIFE 的模型按当前工作目录解析，必须以引擎目录为 cwd。
- 所有子进程不经过 shell，参数以列表传递，支持中文/空格路径。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Iterable, Optional

from .logger import TaskLogger

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# MP4 中可直接复制的音频编码；其余转 AAC
COPY_OK_AUDIO = {"aac", "mp3", "ac3", "eac3", "alac"}


class EngineError(RuntimeError):
    def __init__(
        self,
        stage: str,
        message: str,
        command: Optional[Iterable[str]] = None,
        returncode: Optional[int] = None,
        log_tail: str = "",
    ):
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.command = list(command) if command else []
        self.returncode = returncode
        self.log_tail = log_tail

    def short(self) -> str:
        if self.returncode is None:
            return f"{self.stage}失败：{self.message}"
        return f"{self.stage}失败（退出码 {self.returncode}）：{self.message}"


class CancelledError(RuntimeError):
    pass


@dataclass
class MediaInfo:
    path: Path
    duration: float
    fps: float
    width: int
    height: int
    video_codec: str
    audio_codec: str | None

    @property
    def has_audio(self) -> bool:
        return self.audio_codec is not None


# ---------------- 路径 ----------------
def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def engines_root() -> Path:
    override = os.environ.get("NEX_ENGINES_DIR")
    if override:
        return Path(override)
    return app_root() / "engines"


def ffmpeg_exe() -> Path:
    return engines_root() / "ffmpeg" / "bin" / "ffmpeg.exe"


def ffprobe_exe() -> Path:
    return engines_root() / "ffmpeg" / "bin" / "ffprobe.exe"


def realesrgan_dir() -> Path:
    return engines_root() / "realesrgan"


def realesrgan_exe() -> Path:
    return realesrgan_dir() / "realesrgan-ncnn-vulkan.exe"


def rife_dir() -> Path:
    return engines_root() / "rife"


def rife_exe() -> Path:
    return rife_dir() / "rife-ncnn-vulkan.exe"


def check_engines() -> list[str]:
    """返回缺失的引擎文件列表；为空表示就绪。"""
    missing = []
    for path in (ffmpeg_exe(), ffprobe_exe(), realesrgan_exe(), rife_exe()):
        if not path.exists():
            missing.append(str(path))
    return missing


# ---------------- 探测 ----------------
def _parse_rate(value: str | None) -> float:
    if not value or value in ("0/0", "0"):
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(path: str | Path) -> MediaInfo:
    path = Path(path)
    if not path.exists():
        raise EngineError("探测", f"文件不存在：{path}")
    cmd = [
        str(ffprobe_exe()),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    if proc.returncode != 0:
        raise EngineError(
            "探测", "无法读取视频信息", command=cmd,
            returncode=proc.returncode, log_tail=(proc.stderr or "")[-1200:],
        )
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise EngineError("探测", "视频信息解析失败", command=cmd)
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise EngineError("探测", "文件中没有视频流")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = 0.0
    for candidate in (
        (data.get("format") or {}).get("duration"),
        video.get("duration"),
    ):
        try:
            duration = float(candidate)
            if duration > 0:
                break
        except (TypeError, ValueError):
            continue
    fps = _parse_rate(video.get("avg_frame_rate")) or _parse_rate(
        video.get("r_frame_rate")
    )
    if fps <= 0:
        raise EngineError("探测", "无法识别视频帧率")
    return MediaInfo(
        path=path,
        duration=duration,
        fps=fps,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        video_codec=str(video.get("codec_name") or ""),
        audio_codec=str(audio.get("codec_name")) if audio else None,
    )


# ---------------- 子进程 ----------------
def _tail(path: Path, limit: int = 1200) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-limit:].decode("utf-8", errors="replace")


def _kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _last_time_us(progress_file: Path) -> float:
    try:
        text = progress_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0.0
    for line in reversed(text.splitlines()):
        if line.startswith("out_time_us="):
            try:
                return int(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                continue
        if line.startswith("out_time_ms="):
            try:
                return int(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                continue
    return 0.0


def run_process(
    cmd: list[str],
    cwd: Path,
    log_path: Path,
    cancel,
    poll: Optional[Callable[[], None]] = None,
    stage: str = "引擎",
    interval: float = 0.4,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log_file:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=log_file,
                stderr=log_file,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as exc:
            raise EngineError(stage, f"无法启动引擎：{exc}", command=cmd)
        try:
            while proc.poll() is None:
                if cancel is not None and cancel.is_set():
                    _kill_tree(proc.pid)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise CancelledError("任务已取消")
                if poll is not None:
                    try:
                        poll()
                    except Exception:
                        pass
                time.sleep(interval)
        except KeyboardInterrupt:
            _kill_tree(proc.pid)
            raise CancelledError("任务已取消")
    if proc.returncode != 0:
        raise EngineError(
            stage,
            f"引擎执行失败（退出码 {proc.returncode}）",
            command=cmd,
            returncode=proc.returncode,
            log_tail=_tail(log_path),
        )


def count_video_frames(path: str | Path) -> int:
    """读取视频容器记录的帧数（不进行全量解码）。"""
    cmd = [
        str(ffprobe_exe()),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames",
        "-of", "csv=p=0",
        str(path),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", creationflags=CREATE_NO_WINDOW,
    )
    if proc.returncode != 0:
        return 0
    try:
        return int((proc.stdout or "").strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0


def count_frames(directory: Path) -> int:
    try:
        with os.scandir(directory) as entries:
            return sum(
                1 for e in entries
                if e.is_file() and e.name.lower().endswith((".png", ".jpg", ".jpeg"))
            )
    except OSError:
        return 0


# ---------------- 阶段 ----------------
def extract_frames(
    input_path: Path,
    frames_dir: Path,
    info: MediaInfo,
    log_path: Path,
    cancel,
    on_progress: Optional[Callable[[float], None]] = None,
) -> int:
    frames_dir.mkdir(parents=True, exist_ok=True)
    progress_file = frames_dir.parent / "ffmpeg_extract_progress.txt"
    try:
        progress_file.unlink()
    except OSError:
        pass
    cmd = [
        str(ffmpeg_exe()),
        "-y", "-hide_banner", "-loglevel", "error",
        "-progress", str(progress_file), "-nostats",
        "-i", str(input_path),
        "-fps_mode", "passthrough",
        str(frames_dir / "%08d.png"),
    ]

    def poll() -> None:
        if on_progress and info.duration > 0:
            on_progress(min(1.0, _last_time_us(progress_file) / info.duration))

    run_process(cmd, app_root(), log_path, cancel, poll, stage="抽帧")
    return count_frames(frames_dir)


def run_sr(
    input_dir: Path,
    output_dir: Path,
    model: str,
    scale: int,
    gpu_id: int,
    log_path: Path,
    cancel,
    total_frames: int,
    on_progress: Optional[Callable[[float], None]] = None,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(realesrgan_exe()),
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-n", model,
        "-s", str(scale),
        "-f", "png",
        "-g", str(gpu_id),
    ]

    def poll() -> None:
        if on_progress:
            on_progress(min(1.0, count_frames(output_dir) / max(1, total_frames)))

    run_process(cmd, realesrgan_dir(), log_path, cancel, poll, stage="超分")
    return count_frames(output_dir)


def run_fi(
    input_dir: Path,
    output_dir: Path,
    model: str,
    gpu_id: int,
    log_path: Path,
    cancel,
    total_frames: int,
    on_progress: Optional[Callable[[float], None]] = None,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(rife_exe()),
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-m", model,
        "-g", str(gpu_id),
    ]
    expected = max(1, total_frames * 2)

    def poll() -> None:
        if on_progress:
            on_progress(min(1.0, count_frames(output_dir) / expected))

    run_process(cmd, rife_dir(), log_path, cancel, poll, stage="补帧")
    return count_frames(output_dir)


def encode_video(
    frames_dir: Path,
    frame_fps: float,
    audio_source: Path,
    has_audio: bool,
    audio_codec: str | None,
    output_path: Path,
    target_width: int,
    target_height: int,
    target_fps: float,
    encoder: str,
    crf: int,
    preset: str,
    progress_file: Path,
    log_path: Path,
    cancel,
    duration: float,
    on_progress: Optional[Callable[[float], None]] = None,
) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise EngineError("合成", f"无法创建输出目录：{exc}")
    try:
        progress_file.unlink()
    except OSError:
        pass

    vf = (
        f"fps={target_fps:g},"
        f"scale={target_width}:{target_height}:flags=lanczos"
    )
    cmd = [
        str(ffmpeg_exe()),
        "-y", "-hide_banner", "-loglevel", "error",
        "-progress", str(progress_file), "-nostats",
        "-framerate", f"{frame_fps:g}",
        "-i", str(frames_dir / "%08d.png"),
        "-i", str(audio_source),
        "-map", "0:v:0", "-map", "1:a?",
    ]
    if has_audio:
        if audio_codec in COPY_OK_AUDIO:
            cmd += ["-c:a", "copy"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]

    cmd += ["-vf", vf]
    if encoder == "nvenc":
        cmd += [
            "-c:v", "h264_nvenc", "-cq", str(crf), "-preset", "p7",
            "-pix_fmt", "yuv420p",
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p",
        ]
    cmd += ["-movflags", "+faststart", "-shortest", str(output_path)]

    def poll() -> None:
        if on_progress and duration > 0:
            on_progress(min(1.0, _last_time_us(progress_file) / duration))

    run_process(cmd, app_root(), log_path, cancel, poll, stage="合成")
