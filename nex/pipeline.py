"""处理管线：抽帧 → 超分（可选）→ 补帧（可选）→ 合成。"""

from __future__ import annotations

import math
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import engines
from .engines import CancelledError, EngineError, MediaInfo
from .logger import TaskLogger

ProgressCallback = Optional[Callable[[str, float, str], None]]

SR_SCALES = {
    "realesr-animevideov3": {2, 3, 4},
    "realesrgan-x4plus": {4},
    "realesrgan-x4plus-anime": {4},
}
FI_MODELS = {
    "rife", "rife-HD", "rife-UHD", "rife-anime", "rife-v2",
    "rife-v2.3", "rife-v2.4", "rife-v3.0", "rife-v3.1",
    "rife-v4", "rife-v4.6",
}


class PipelineError(RuntimeError):
    pass


@dataclass
class SROptions:
    enabled: bool = False
    model: str = "realesr-animevideov3"
    scale: int | None = None
    target_height: int | None = None


@dataclass
class FIOptions:
    enabled: bool = False
    model: str = "rife-v4.6"
    multiplier: int | None = None
    target_fps: float | None = None


@dataclass
class EncodeOptions:
    encoder: str = "auto"  # auto / x264 / nvenc
    crf: int = 18
    preset: str = "medium"


@dataclass
class PipelineOptions:
    input_path: Path
    output_dir: Path | None = None
    output_path: Path | None = None
    sr: SROptions = field(default_factory=SROptions)
    fi: FIOptions = field(default_factory=FIOptions)
    encode: EncodeOptions = field(default_factory=EncodeOptions)
    gpu_id: int = 0
    keep_temp: bool = False


@dataclass
class PipelineResult:
    output_path: Path
    log_path: Path
    width: int
    height: int
    fps: float
    frames: int
    elapsed: float


def _even(value: float) -> int:
    number = int(round(value))
    if number % 2:
        number -= 1
    return max(2, number)


def _plan_sr(sr: SROptions, info: MediaInfo) -> dict | None:
    if not sr.enabled:
        return None
    if sr.model not in SR_SCALES:
        raise PipelineError(f"未知的超分模型：{sr.model}")
    if sr.scale is not None and sr.target_height is not None:
        raise PipelineError("超分倍数与目标高度只能二选一")

    requested = sr.scale
    if requested is None and sr.target_height:
        requested = max(1, math.ceil(sr.target_height / info.height))
    if requested is None:
        requested = 2
    requested = max(1, int(requested))

    supported = SR_SCALES[sr.model]
    run_scale = requested if requested in supported else 4

    if requested == 1:
        if sr.target_height:
            height = _even(sr.target_height)
            width = _even(info.width * height / info.height)
        else:
            width, height = _even(info.width), _even(info.height)
        return {
            "skip": True, "scale": 1,
            "final_w": width, "final_h": height,
        }

    if sr.target_height:
        final_h = _even(sr.target_height)
        final_w = _even(info.width * final_h / info.height)
    else:
        final_w = _even(info.width * requested)
        final_h = _even(info.height * requested)

    return {
        "skip": False,
        "scale": run_scale,
        "final_w": final_w,
        "final_h": final_h,
    }


def _plan_fi(fi: FIOptions, info: MediaInfo) -> tuple[int, float, str]:
    """返回 (插值遍数, 输出帧率, 说明)。"""
    if not fi.enabled:
        return 0, info.fps, "未启用"
    if fi.model not in FI_MODELS:
        raise PipelineError(f"未知的补帧模型：{fi.model}")
    if fi.multiplier is not None and fi.target_fps is not None:
        raise PipelineError("补帧倍数与目标帧率只能二选一")

    if fi.multiplier is not None:
        if fi.multiplier not in (2, 4):
            raise PipelineError("补帧倍数仅支持 2x 或 4x")
        passes = 1 if fi.multiplier == 2 else 2
        return passes, info.fps * fi.multiplier, f"{fi.multiplier}x"

    if fi.target_fps is not None:
        target = float(fi.target_fps)
        if target <= info.fps + 1e-6:
            return 0, info.fps, f"目标 {target:g}fps 不高于源帧率，跳过"
        passes = 0
        fps = info.fps
        while fps < target - 1e-6 and passes < 3:
            fps *= 2
            passes += 1
        if fps + 1e-6 < target:
            return passes, fps, f"目标 {target:g}fps 超过 8x，已限制为 {fps:g}fps"
        return passes, target, f"目标 {target:g}fps"

    return 1, info.fps * 2, "2x"


def _choose_output(options: PipelineOptions, info: MediaInfo) -> Path:
    if options.output_path:
        return Path(options.output_path)
    base = Path(options.output_dir) if options.output_dir else info.path.parent
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PipelineError(f"无法创建输出目录：{exc}")
    stem = info.path.stem
    candidate = base / f"{stem}_NEX.mp4"
    index = 1
    while candidate.exists():
        candidate = base / f"{stem}_NEX_{index}.mp4"
        index += 1
    return candidate


def _check_cancel(cancel) -> None:
    if cancel is not None and cancel.is_set():
        raise CancelledError("任务已取消")


def run_pipeline(
    options: PipelineOptions,
    on_progress: ProgressCallback = None,
    cancel: threading.Event | None = None,
) -> PipelineResult:
    started = time.time()
    cancel = cancel or threading.Event()
    task_id = uuid.uuid4().hex[:12]
    logger = TaskLogger(task_id)
    temp_root = Path(tempfile.gettempdir()) / "NEX" / task_id

    result_info: dict = {}
    try:
        missing = engines.check_engines()
        if missing:
            raise PipelineError("缺少引擎文件：\n" + "\n".join(missing))

        input_path = Path(options.input_path)
        info = engines.probe(input_path)
        logger.log(
            "探测",
            f"{input_path.name} · {info.width}x{info.height} · "
            f"{info.fps:.3f}fps · {info.duration:.2f}s · "
            f"音轨 {info.audio_codec or '无'}",
        )

        if not options.sr.enabled and not options.fi.enabled:
            raise PipelineError("请至少开启超分或补帧中的一项")

        sr_plan = _plan_sr(options.sr, info)
        fi_passes, final_fps, fi_note = _plan_fi(options.fi, info)
        have_sr = sr_plan is not None and not sr_plan["skip"]
        have_fi = fi_passes > 0
        if not have_sr and not have_fi:
            raise PipelineError("没有可执行的增强步骤（超分被跳过且补帧未生效）")

        if sr_plan is not None:
            logger.log(
                "规划",
                f"超分：{options.sr.model}，运行倍数 {sr_plan['scale']}x"
                + ("（跳过 AI，直接缩放）" if sr_plan["skip"] else "")
                + f"，输出 {sr_plan['final_w']}x{sr_plan['final_h']}",
            )
        logger.log(
            "规划",
            f"补帧：{options.fi.model if options.fi.enabled else '未启用'}，"
            f"{fi_note}，插值 {fi_passes} 遍，输出 {final_fps:.3f}fps",
        )

        weights: dict[str, float] = {"抽帧": 5.0}
        if have_sr:
            weights["超分"] = 40.0
        if have_fi:
            weights["补帧"] = 40.0 if have_sr else 60.0
        weights["合成"] = 100.0 - sum(weights.values())
        offsets: dict[str, float] = {}
        cursor = 0.0
        for stage in ("抽帧", "超分", "补帧", "合成"):
            if stage in weights:
                offsets[stage] = cursor
                cursor += weights[stage]

        def emit(stage: str, fraction: float, message: str = "") -> None:
            if on_progress is None:
                return
            fraction = max(0.0, min(1.0, fraction))
            overall = offsets[stage] + weights[stage] * fraction
            on_progress(stage, overall, message)

        temp_root.mkdir(parents=True, exist_ok=True)

        # 1. 抽帧
        _check_cancel(cancel)
        frames_dir = temp_root / "frames_in"
        emit("抽帧", 0.0, "开始")
        logger.log("抽帧", "开始")
        emit_started = time.time()
        frame_count = engines.extract_frames(
            input_path, frames_dir, info, logger.path, cancel,
            on_progress=lambda f: emit("抽帧", f, "读取中"),
        )
        if frame_count <= 0:
            raise PipelineError("抽帧失败：没有生成任何帧")
        logger.log(
            "抽帧",
            f"完成：{frame_count} 帧，耗时 {time.time() - emit_started:.1f}s",
        )
        emit("抽帧", 1.0, f"{frame_count} 帧")
        current_frames = frames_dir
        frame_count_after = frame_count

        # 2. 超分
        if have_sr:
            _check_cancel(cancel)
            sr_out = temp_root / "frames_sr"
            scale = sr_plan["scale"]
            logger.log(
                "超分",
                f"开始：{options.sr.model} {scale}x，共 {frame_count_after} 帧",
            )
            emit("超分", 0.0, "开始")
            stage_started = time.time()

            def sr_cb(fraction: float, total: int = frame_count_after) -> None:
                emit("超分", fraction, f"{int(fraction * total)}/{total} 帧")

            new_count = engines.run_sr(
                current_frames, sr_out, options.sr.model, scale,
                options.gpu_id, logger.path, cancel, frame_count_after, sr_cb,
            )
            if new_count <= 0:
                raise PipelineError("超分失败：没有生成任何帧")
            logger.log(
                "超分",
                f"完成：{new_count} 帧，耗时 {time.time() - stage_started:.1f}s",
            )
            emit("超分", 1.0, f"{new_count} 帧")
            current_frames = sr_out
            frame_count_after = new_count

        # 3. 补帧
        if have_fi:
            for pass_index in range(1, fi_passes + 1):
                _check_cancel(cancel)
                fi_out = temp_root / f"frames_fi_{pass_index}"
                logger.log(
                    "补帧",
                    f"第 {pass_index}/{fi_passes} 遍开始：{frame_count_after} 帧",
                )
                stage_started = time.time()
                total_in = frame_count_after

                def fi_cb(
                    fraction: float,
                    total: int = total_in,
                    index: int = pass_index,
                ) -> None:
                    overall = ((index - 1) + fraction) / fi_passes
                    emit("补帧", overall, f"第 {index}/{fi_passes} 遍")

                new_count = engines.run_fi(
                    current_frames, fi_out, options.fi.model,
                    options.gpu_id, logger.path, cancel, total_in, fi_cb,
                )
                if new_count <= 0:
                    raise PipelineError("补帧失败：没有生成任何帧")
                logger.log(
                    "补帧",
                    f"第 {pass_index} 遍完成：{new_count} 帧，"
                    f"耗时 {time.time() - stage_started:.1f}s",
                )
                current_frames = fi_out
                frame_count_after = new_count
            emit("补帧", 1.0, f"{frame_count_after} 帧")

        # 4. 合成
        _check_cancel(cancel)
        if sr_plan is not None:
            final_w = sr_plan["final_w"]
            final_h = sr_plan["final_h"]
        else:
            final_w, final_h = _even(info.width), _even(info.height)
        output_path = _choose_output(options, info)
        encoder = options.encode.encoder
        if encoder == "auto":
            encoder = "x264"
            logger.log(
                "合成",
                "编码器 auto → x264（NVENC 需驱动 ≥610.00，暂用软件编码）",
            )
        logger.log(
            "合成",
            f"开始：{final_w}x{final_h} @ {final_fps:.3f}fps，编码器 {encoder}",
        )
        emit("合成", 0.0, "开始")
        stage_started = time.time()
        progress_file = temp_root / "ffmpeg_encode_progress.txt"
        encode_args = dict(
            frames_dir=current_frames,
            frame_fps=info.fps * (2 ** fi_passes),
            audio_source=input_path,
            has_audio=info.has_audio,
            audio_codec=info.audio_codec,
            output_path=output_path,
            target_width=final_w,
            target_height=final_h,
            target_fps=final_fps,
            crf=options.encode.crf,
            preset=options.encode.preset,
            progress_file=progress_file,
            log_path=logger.path,
            cancel=cancel,
            duration=info.duration,
            on_progress=lambda f: emit("合成", f, "写入中"),
        )
        try:
            engines.encode_video(encoder=encoder, **encode_args)
        except EngineError as exc:
            if encoder == "nvenc":
                logger.log("合成", "NVENC 失败，自动回退 x264：" + exc.short())
                encoder = "x264"
                engines.encode_video(encoder=encoder, **encode_args)
            else:
                raise
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PipelineError("合成失败：输出文件不存在或为空")
        logger.log(
            "合成",
            f"完成：{output_path}，耗时 {time.time() - stage_started:.1f}s",
        )
        emit("合成", 1.0, str(output_path.name))

        final_frames = engines.count_video_frames(output_path) or frame_count_after
        elapsed = time.time() - started
        logger.log(
            "完成",
            f"总耗时 {elapsed:.1f}s · 输出 {final_w}x{final_h} @ "
            f"{final_fps:.3f}fps · {final_frames} 帧",
        )
        result_info = {
            "output": output_path,
            "width": final_w,
            "height": final_h,
            "fps": final_fps,
            "frames": final_frames,
            "elapsed": elapsed,
        }
    except (EngineError, PipelineError, CancelledError) as exc:
        try:
            setattr(exc, "log_path", str(logger.path))
        except Exception:
            pass
        logger.log("错误", str(exc))
        raise
    finally:
        logger.close()
        if not options.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)

    return PipelineResult(
        output_path=result_info["output"],
        log_path=logger.path,
        width=result_info["width"],
        height=result_info["height"],
        fps=result_info["fps"],
        frames=result_info["frames"],
        elapsed=result_info["elapsed"],
    )
