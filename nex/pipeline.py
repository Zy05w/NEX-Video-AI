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

from . import engines, gpu, paths, storage
from .engines import CancelledError, EngineError, MediaInfo
from .errors import friendly_os_error
from .i18n import t
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
    "rife-v4", "rife-v4.6", engines.PRACTICAL_RIFE_MODEL,
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
    task_id: str | None = None
    output_dir: Path | None = None
    output_path: Path | None = None
    sr: SROptions = field(default_factory=SROptions)
    fi: FIOptions = field(default_factory=FIOptions)
    encode: EncodeOptions = field(default_factory=EncodeOptions)
    gpu_id: int = 0
    keep_temp: bool = False
    temp_guard: bool = True
    temp_limit: float = 88.0


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
        raise PipelineError(t("未知的超分模型：{model}", model=sr.model))
    if sr.scale is not None and sr.target_height is not None:
        raise PipelineError(t("超分倍数与目标高度只能二选一"))

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
        return 0, info.fps, t("未启用")
    if fi.model not in FI_MODELS:
        raise PipelineError(t("未知的补帧模型：{model}", model=fi.model))
    if fi.multiplier is not None and fi.target_fps is not None:
        raise PipelineError(t("补帧倍数与目标帧率只能二选一"))

    if fi.multiplier is not None:
        if fi.multiplier not in (2, 4):
            raise PipelineError(t("补帧倍数仅支持 2x 或 4x"))
        passes = 1 if fi.multiplier == 2 else 2
        return passes, info.fps * fi.multiplier, f"{fi.multiplier}x"

    if fi.target_fps is not None:
        target = float(fi.target_fps)
        if target <= info.fps + 1e-6:
            return 0, info.fps, t(
                "目标 {target}fps 不高于源帧率，跳过", target=f"{target:g}"
            )
        passes = 0
        fps = info.fps
        while fps < target - 1e-6 and passes < 3:
            fps *= 2
            passes += 1
        if fps + 1e-6 < target:
            return passes, fps, t(
                "目标 {target}fps 超过 8x，已限制为 {fps}fps",
                target=f"{target:g}",
                fps=f"{fps:g}",
            )
        return passes, target, t("目标 {target}fps", target=f"{target:g}")

    return 1, info.fps * 2, "2x"


def _choose_output(options: PipelineOptions, info: MediaInfo) -> Path:
    if options.output_path:
        return Path(options.output_path)
    base = Path(options.output_dir) if options.output_dir else info.path.parent
    try:
        paths.makedirs(base)
    except OSError as exc:
        raise PipelineError(
            t(
                "无法创建输出目录：{error}",
                error=friendly_os_error(exc, base),
            )
        )
    stem = info.path.stem
    candidate = base / f"{stem}_NEX.mp4"
    index = 1
    while paths.exists(candidate):
        candidate = base / f"{stem}_NEX_{index}.mp4"
        index += 1
    return candidate


def cleanup_stale_temp(max_age_hours: float = 24.0) -> int:
    """清理异常退出遗留的临时目录（默认只清理 24 小时前的）。"""
    root = Path(tempfile.gettempdir()) / "NEX"
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    try:
        entries = list(root.iterdir())
    except OSError:
        return 0
    for child in entries:
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


def _check_cancel(cancel) -> None:
    if cancel is not None and cancel.is_set():
        raise CancelledError(t("任务已取消"))


def run_pipeline(
    options: PipelineOptions,
    on_progress: ProgressCallback = None,
    cancel: threading.Event | None = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    started = time.time()
    cancel = cancel or threading.Event()
    task_id = options.task_id or uuid.uuid4().hex[:12]
    logger = TaskLogger(task_id, on_line=on_log)
    temp_root = Path(tempfile.gettempdir()) / "NEX" / task_id
    monitor: gpu.GpuMonitor | None = None

    result_info: dict = {}
    try:
        missing = engines.check_engines()
        if missing:
            raise PipelineError(
                t("缺少引擎文件：\n{files}", files="\n".join(missing))
            )

        input_path = Path(options.input_path)
        info = engines.probe(input_path)
        logger.log(
            "探测",
            t(
                "{name} · {width}x{height} · {fps}fps · {duration}s · 音轨 {audio}",
                name=input_path.name,
                width=info.width,
                height=info.height,
                fps=f"{info.fps:.3f}",
                duration=f"{info.duration:.2f}",
                audio=info.audio_codec or t("无"),
            ),
        )

        if info.duration <= 0:
            logger.log(
                "磁盘", t("视频时长未知，磁盘预检仅作粗略估算")
            )

        if not options.sr.enabled and not options.fi.enabled:
            raise PipelineError(t("请至少开启超分或补帧中的一项"))

        if (
            options.fi.enabled
            and options.fi.model == engines.PRACTICAL_RIFE_MODEL
        ):
            missing = engines.check_practical_rife()
            if missing:
                raise PipelineError(
                    t(
                        "Practical-RIFE 4.25 环境不完整：\n{files}",
                        files="\n".join(missing),
                    )
                )

        sr_plan = _plan_sr(options.sr, info)
        fi_passes, final_fps, fi_note = _plan_fi(options.fi, info)
        have_sr = sr_plan is not None and not sr_plan["skip"]
        have_fi = fi_passes > 0
        if not have_sr and not have_fi:
            raise PipelineError(
                t("没有可执行的增强步骤（超分被跳过且补帧未生效）")
            )

        if sr_plan is not None:
            if sr_plan["skip"]:
                plan_message = t(
                    "超分：{model}，运行倍数 {scale}x（跳过 AI，直接缩放），"
                    "输出 {width}x{height}",
                    model=options.sr.model,
                    scale=sr_plan["scale"],
                    width=sr_plan["final_w"],
                    height=sr_plan["final_h"],
                )
            else:
                plan_message = t(
                    "超分：{model}，运行倍数 {scale}x，输出 {width}x{height}",
                    model=options.sr.model,
                    scale=sr_plan["scale"],
                    width=sr_plan["final_w"],
                    height=sr_plan["final_h"],
                )
            logger.log("规划", plan_message)
        if options.fi.enabled:
            logger.log(
                "规划",
                t(
                    "补帧：{model}，{note}，插值 {passes} 遍，输出 {fps}fps",
                    model=options.fi.model,
                    note=fi_note,
                    passes=fi_passes,
                    fps=f"{final_fps:.3f}",
                ),
            )
        else:
            logger.log("规划", t("补帧：未启用"))

        if sr_plan is not None:
            final_w = sr_plan["final_w"]
            final_h = sr_plan["final_h"]
        else:
            final_w, final_h = _even(info.width), _even(info.height)

        output_path = _choose_output(options, info)
        try:
            storage.ensure_writable(output_path.parent)
        except OSError as exc:
            raise PipelineError(
                t(
                    "输出位置不可写：{error}",
                    error=friendly_os_error(exc, output_path.parent),
                )
            )

        temp_required = storage.estimate_temp_bytes(
            info, sr_plan, fi_passes, keep_temp=options.keep_temp
        )
        output_required = storage.estimate_output_bytes(
            info, final_w, final_h, final_fps
        )
        temp_free = storage.free_bytes(temp_root)
        output_free = storage.free_bytes(output_path.parent)
        logger.log(
            "磁盘",
            t(
                "磁盘预检：临时空间预计 {temp}，可用 {temp_free}；"
                "输出预计 {output}，可用 {output_free}",
                temp=storage.format_size(temp_required),
                temp_free=(
                    storage.format_size(temp_free)
                    if temp_free is not None
                    else t("未知")
                ),
                output=storage.format_size(output_required),
                output_free=(
                    storage.format_size(output_free)
                    if output_free is not None
                    else t("未知")
                ),
            ),
        )
        issues = storage.check_disk_space(
            temp_root, temp_required, output_path.parent, output_required
        )
        if issues:
            raise PipelineError(
                t(
                    "磁盘空间不足，无法开始处理：\n{issues}\n\n"
                    "请清理磁盘空间后重试；也可以把输出位置改到空间更大的磁盘。",
                    issues="\n\n".join(issue.message() for issue in issues),
                )
            )

        if options.temp_guard:
            status = gpu.query_gpu()
            if status is not None:
                logger.log(
                    "温度",
                    t(
                        "显卡 {name} · 初始 {temp}°C · 保护上限 {limit}°C",
                        name=status.name,
                        temp=status.temperature,
                        limit=f"{options.temp_limit:g}",
                    ),
                )
                monitor = gpu.GpuMonitor(
                    logger, cancel, limit=options.temp_limit
                )
                monitor.start()
            else:
                logger.log(
                    "温度", t("未检测到 nvidia-smi，跳过温度监控")
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

        try:
            paths.makedirs(temp_root)
        except OSError as exc:
            raise PipelineError(
                t(
                    "无法创建临时工作目录：{error}",
                    error=friendly_os_error(exc, temp_root),
                )
            )

        # 1. 抽帧
        _check_cancel(cancel)
        frames_dir = temp_root / "frames_in"
        emit("抽帧", 0.0, t("开始"))
        logger.log("抽帧", t("开始"))
        emit_started = time.time()
        frame_count = engines.extract_frames(
            input_path, frames_dir, info, logger.path, cancel,
            on_progress=lambda f: emit("抽帧", f, "读取中"),
        )
        if frame_count <= 0:
            raise PipelineError(t("抽帧失败：没有生成任何帧"))
        logger.log(
            "抽帧",
            t(
                "完成：{count} 帧，耗时 {seconds}s",
                count=frame_count,
                seconds=f"{time.time() - emit_started:.1f}",
            ),
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
                t(
                    "开始：{model} {scale}x，共 {count} 帧",
                    model=options.sr.model,
                    scale=scale,
                    count=frame_count_after,
                ),
            )
            emit("超分", 0.0, t("开始"))
            stage_started = time.time()

            def sr_cb(fraction: float, total: int = frame_count_after) -> None:
                emit("超分", fraction, f"{int(fraction * total)}/{total} 帧")

            new_count = engines.run_sr(
                current_frames, sr_out, options.sr.model, scale,
                options.gpu_id, logger.path, cancel, frame_count_after, sr_cb,
            )
            if new_count <= 0:
                raise PipelineError(t("超分失败：没有生成任何帧"))
            logger.log(
                "超分",
                t(
                    "完成：{count} 帧，耗时 {seconds}s",
                    count=new_count,
                    seconds=f"{time.time() - stage_started:.1f}",
                ),
            )
            emit("超分", 1.0, f"{new_count} 帧")
            current_frames = sr_out
            frame_count_after = new_count
            if not options.keep_temp:
                shutil.rmtree(frames_dir, ignore_errors=True)

        # 3. 补帧
        if have_fi:
            for pass_index in range(1, fi_passes + 1):
                _check_cancel(cancel)
                fi_out = temp_root / f"frames_fi_{pass_index}"
                logger.log(
                    "补帧",
                    t(
                        "第 {index}/{total} 遍开始：{count} 帧",
                        index=pass_index,
                        total=fi_passes,
                        count=frame_count_after,
                    ),
                )
                stage_started = time.time()
                total_in = frame_count_after
                input_frames = current_frames

                def fi_cb(
                    fraction: float,
                    total: int = total_in,
                    index: int = pass_index,
                ) -> None:
                    overall = ((index - 1) + fraction) / fi_passes
                    emit("补帧", overall, f"第 {index}/{fi_passes} 遍")

                if options.fi.model == engines.PRACTICAL_RIFE_MODEL:
                    pt_progress = (
                        temp_root / f"rife_pt_progress_{pass_index}.txt"
                    )
                    new_count = engines.run_fi_pytorch(
                        current_frames,
                        fi_out,
                        engines.practical_rife_model_dir(),
                        2,
                        1.0,
                        True,
                        pt_progress,
                        logger.path,
                        cancel,
                        total_in,
                        fi_cb,
                    )
                else:
                    new_count = engines.run_fi(
                        current_frames, fi_out, options.fi.model,
                        options.gpu_id, logger.path, cancel, total_in,
                        fi_cb,
                    )
                if new_count <= 0:
                    raise PipelineError(t("补帧失败：没有生成任何帧"))
                logger.log(
                    "补帧",
                    t(
                        "第 {index} 遍完成：{count} 帧，耗时 {seconds}s",
                        index=pass_index,
                        count=new_count,
                        seconds=f"{time.time() - stage_started:.1f}",
                    ),
                )
                current_frames = fi_out
                frame_count_after = new_count
                if not options.keep_temp:
                    shutil.rmtree(input_frames, ignore_errors=True)
            emit("补帧", 1.0, f"{frame_count_after} 帧")

        # 4. 合成
        _check_cancel(cancel)
        encoder = options.encode.encoder
        if encoder == "auto":
            encoder = "x264"
            logger.log(
                "合成",
                t("编码器 auto → x264（NVENC 需驱动 ≥610.00，暂用软件编码）"),
            )
        logger.log(
            "合成",
            t(
                "开始：{width}x{height} @ {fps}fps，编码器 {encoder}",
                width=final_w,
                height=final_h,
                fps=f"{final_fps:.3f}",
                encoder=encoder,
            ),
        )
        emit("合成", 0.0, t("开始"))
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
                logger.log(
                    "合成",
                    t(
                        "NVENC 失败，自动回退 x264：{message}",
                        message=exc.short(),
                    ),
                )
                encoder = "x264"
                engines.encode_video(encoder=encoder, **encode_args)
            else:
                raise
        if not paths.exists(output_path) or paths.file_size(output_path) == 0:
            raise PipelineError(
                t(
                    "输出文件写入失败。"
                    "请检查输出位置是否可写、磁盘空间是否充足。"
                )
            )
        logger.log(
            "合成",
            t(
                "完成：{path}，耗时 {seconds}s",
                path=output_path,
                seconds=f"{time.time() - stage_started:.1f}",
            ),
        )
        emit("合成", 1.0, str(output_path.name))

        final_frames = engines.count_video_frames(output_path) or frame_count_after
        elapsed = time.time() - started
        logger.log(
            "完成",
            t(
                "总耗时 {seconds}s · 输出 {width}x{height} @ {fps}fps · {frames} 帧",
                seconds=f"{elapsed:.1f}",
                width=final_w,
                height=final_h,
                fps=f"{final_fps:.3f}",
                frames=final_frames,
            ),
        )
        result_info = {
            "output": output_path,
            "width": final_w,
            "height": final_h,
            "fps": final_fps,
            "frames": final_frames,
            "elapsed": elapsed,
        }
    except CancelledError as exc:
        if monitor is not None and monitor.overheated:
            error = PipelineError(
                t(
                    "显卡温度过高（{temp}°C，保护上限 {limit}°C），"
                    "已安全停止任务。请检查散热后重试。",
                    temp=monitor.max_temp,
                    limit=f"{options.temp_limit:g}",
                )
            )
            setattr(error, "log_path", str(logger.path))
            logger.log("错误", str(error))
            raise error
        setattr(exc, "log_path", str(logger.path))
        logger.log("取消", t("任务已取消"))
        raise
    except (EngineError, PipelineError) as exc:
        setattr(exc, "log_path", str(logger.path))
        logger.log("错误", str(exc))
        if isinstance(exc, EngineError):
            engine_log = logger.path.with_name(
                f"{logger.path.stem}.engine.log"
            )
            if paths.exists(engine_log):
                logger.log(
                    "错误",
                    t("引擎原始输出：{path}", path=engine_log),
                )
        raise
    except OSError as exc:
        target = getattr(exc, "filename", None) or options.input_path
        error = PipelineError(friendly_os_error(exc, target))
        setattr(error, "log_path", str(logger.path))
        logger.log("错误", str(error))
        raise error
    finally:
        if monitor is not None:
            monitor.stop()
            monitor.join(timeout=2)
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
