"""命令行处理入口（S3）：headless 验证处理管线。

示例：
  python -m nex.cli 输入.mp4 --sr realesr-animevideov3 --sr-scale 2
  python -m nex.cli 输入.mp4 --fi rife-v4.6 --fi-mult 2
  python -m nex.cli 输入.mp4 --sr realesr-animevideov3 --sr-height 1080 \
      --fi rife-v4.6 --fi-fps 60 --output 输出.mp4
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

from . import engines
from .engines import CancelledError, EngineError, probe
from .pipeline import (
    FI_MODELS,
    SR_SCALES,
    EncodeOptions,
    FIOptions,
    PipelineError,
    PipelineOptions,
    SROptions,
    run_pipeline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nex.cli",
        description="NEX 视频增强 — 命令行处理工具",
    )
    parser.add_argument("input", nargs="?", help="输入视频路径")
    parser.add_argument("--info", action="store_true", help="只读取视频信息")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument(
        "--sr", choices=sorted(SR_SCALES),
        help="启用 AI 超分并指定模型",
    )
    parser.add_argument(
        "--sr-scale", type=int, choices=[2, 3, 4],
        help="超分倍数（与 --sr-height 二选一）",
    )
    parser.add_argument(
        "--sr-height", type=int,
        help="目标高度（如 1080 / 1440 / 2160）",
    )
    parser.add_argument(
        "--fi", choices=sorted(FI_MODELS),
        help="启用 AI 补帧并指定模型",
    )
    parser.add_argument(
        "--fi-mult", type=int, choices=[2, 4],
        help="补帧倍数（与 --fi-fps 二选一）",
    )
    parser.add_argument("--fi-fps", type=float, help="目标帧率")
    parser.add_argument(
        "--encoder", choices=["auto", "x264", "nvenc"], default="auto",
        help="视频编码器（默认 auto → x264）",
    )
    parser.add_argument("--crf", type=int, default=18, help="画质参数（默认 18）")
    parser.add_argument(
        "--preset", default="medium",
        choices=[
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow",
        ],
        help="x264 预设（默认 medium）",
    )
    parser.add_argument("--gpu", type=int, default=0, help="GPU 编号（默认 0）")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    parser.add_argument(
        "--cancel-after", type=float, default=None,
        help=argparse.SUPPRESS,
    )
    return parser


def _print_info(path: Path) -> int:
    info = probe(path)
    print(f"文件：{info.path}")
    print(f"分辨率：{info.width}x{info.height}")
    print(f"帧率：{info.fps:g} fps")
    print(f"时长：{info.duration:g} 秒")
    print(f"视频编码：{info.video_codec}")
    print(f"音频编码：{info.audio_codec or '无'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.error("请提供输入视频路径")
    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"输入文件不存在：{input_path}")

    if args.info:
        try:
            return _print_info(input_path)
        except (EngineError, PipelineError) as exc:
            print(f"读取失败：{exc}", file=sys.stderr)
            return 1

    if not args.sr and not args.fi:
        parser.error("请至少使用 --sr 或 --fi 中的一项")
    if args.sr and args.sr_scale is not None and args.sr_height is not None:
        parser.error("--sr-scale 与 --sr-height 只能二选一")
    if args.fi and args.fi_mult is not None and args.fi_fps is not None:
        parser.error("--fi-mult 与 --fi-fps 只能二选一")
    if not 0 <= args.crf <= 51:
        parser.error("--crf 必须在 0-51 之间")

    cancel = threading.Event()

    def on_sigint(signum, frame):
        cancel.set()

    try:
        signal.signal(signal.SIGINT, on_sigint)
    except (ValueError, OSError):
        pass
    if args.cancel_after:
        threading.Timer(max(0.1, args.cancel_after), cancel.set).start()

    state = {"stage": "", "bucket": -1}

    def on_progress(stage: str, percent: float, message: str) -> None:
        bucket = int(percent // 5)
        if stage != state["stage"] or bucket != state["bucket"]:
            suffix = f"  {message}" if message else ""
            print(f"[{stage}] {percent:5.1f}%{suffix}", flush=True)
            state["stage"] = stage
            state["bucket"] = bucket

    options = PipelineOptions(
        input_path=input_path,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        output_path=Path(args.output) if args.output else None,
        sr=SROptions(
            enabled=bool(args.sr),
            model=args.sr or "realesr-animevideov3",
            scale=args.sr_scale,
            target_height=args.sr_height,
        ),
        fi=FIOptions(
            enabled=bool(args.fi),
            model=args.fi or "rife-v4.6",
            multiplier=args.fi_mult,
            target_fps=args.fi_fps,
        ),
        encode=EncodeOptions(
            encoder=args.encoder,
            crf=args.crf,
            preset=args.preset,
        ),
        gpu_id=args.gpu,
        keep_temp=args.keep_temp,
    )

    try:
        result = run_pipeline(options, on_progress=on_progress, cancel=cancel)
    except CancelledError:
        print("已取消：任务已停止，临时文件已清理。", flush=True)
        return 130
    except (EngineError, PipelineError) as exc:
        print(f"\n处理失败：{exc}", file=sys.stderr)
        log_path = getattr(exc, "log_path", None)
        if log_path:
            print(f"日志：{log_path}", file=sys.stderr)
        if isinstance(exc, EngineError) and exc.log_tail:
            print("引擎输出（末尾）：", file=sys.stderr)
            print(exc.log_tail, file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"\n处理失败：文件或目录无法访问（{exc}）", file=sys.stderr)
        return 1

    print("")
    print(f"已完成：{result.output_path}")
    print(
        f"输出参数：{result.width}x{result.height} · "
        f"{result.fps:g}fps · {result.frames} 帧 · "
        f"耗时 {result.elapsed:.1f} 秒"
    )
    print(f"日志：{result.log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
