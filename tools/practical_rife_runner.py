"""Practical-RIFE 4.25 帧目录推理封装（在独立 PyTorch 环境中运行）。

不直接使用 Practical-RIFE 的 inference_video.py，而是只加载其 IFNet 架构
与 4.25 权重，按帧目录输出 %08d.png，便于接入 NEX 处理管线。

依赖：torch、numpy、opencv-python（见 .venv-rife）
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Practical-RIFE 仓库目录")
    parser.add_argument("--model", required=True, help="包含 flownet.pkl 的目录")
    parser.add_argument("--input", required=True, help="输入帧目录")
    parser.add_argument("--output", required=True, help="输出帧目录")
    parser.add_argument("--multi", type=int, default=2, choices=[2, 4])
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--progress", default="", help="进度文件路径")
    return parser.parse_args()


def load_model(repo: Path, model_dir: Path, device: torch.device):
    sys.path.insert(0, str(repo))
    from train_log.IFNet_HDv3 import IFNet

    model = IFNet()
    model_path = model_dir / "flownet.pkl"
    try:
        state = torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        state = torch.load(model_path, map_location="cpu")
    if any(key.startswith("module.") for key in state):
        state = {
            key.replace("module.", "", 1): value
            for key, value in state.items()
        }
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        raise RuntimeError(f"模型权重缺少参数：{len(missing)} 个")
    if unexpected:
        print(
            f"UNEXPECTED {len(unexpected)} keys, first: {unexpected[:8]}",
            flush=True,
        )
    model.to(device)
    model.eval()
    print(
        f"MODEL version=4.25 device={device} "
        f"unexpected={len(unexpected)}",
        flush=True,
    )
    return model


def read_frame(path: Path, device: torch.device, half: bool, pad):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"无法读取帧：{path}")
    rgb = image[:, :, ::-1].copy()
    tensor = (
        torch.from_numpy(rgb)
        .to(device)
        .permute(2, 0, 1)
        .unsqueeze(0)
        .float()
        / 255.0
    )
    tensor = F.pad(tensor, pad)
    if half:
        tensor = tensor.half()
    return tensor


def to_image(tensor: torch.Tensor, height: int, width: int) -> np.ndarray:
    array = (
        tensor[0].float().clamp(0, 1).cpu().numpy().transpose(1, 2, 0)
    )
    array = (array * 255.0).round().astype(np.uint8)[:height, :width]
    return array[:, :, ::-1]  # RGB -> BGR


def write_frame(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"无法写入帧：{path}")


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    model_dir = Path(args.model).resolve()
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    progress_file = Path(args.progress) if args.progress else None

    frames = sorted(
        input_dir.glob("*.png"),
        key=lambda path: int(path.stem) if path.stem.isdigit() else path.name,
    )
    if not frames:
        raise RuntimeError("输入帧目录没有 PNG 文件")
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.png"):
        old.unlink()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    half = bool(args.fp16 and device.type == "cuda")
    torch.set_grad_enabled(False)
    if device.type == "cuda":
        torch.backends.cudnn.enabled = True
        torch.backends.cudnn.benchmark = True

    model = load_model(repo, model_dir, device)
    if half:
        model.half()
        # 官方 fp16 模式同样设置默认半精度，确保 warp 网格缓存为 half
        torch.set_default_dtype(torch.float16)

    first = cv2.imread(str(frames[0]), cv2.IMREAD_COLOR)
    height, width = first.shape[:2]
    tmp = max(128, int(128 / args.scale))
    pad_h = ((height - 1) // tmp + 1) * tmp
    pad_w = ((width - 1) // tmp + 1) * tmp
    pad = (0, pad_w - width, 0, pad_h - height)
    scale_list = [
        16 / args.scale,
        8 / args.scale,
        4 / args.scale,
        2 / args.scale,
        1 / args.scale,
    ]

    def infer(img0: torch.Tensor, img1: torch.Tensor, timestep: float):
        with torch.inference_mode():
            _, _, merged = model(
                torch.cat((img0, img1), 1), timestep, scale_list
            )
        return merged[-1]

    total_pairs = max(1, len(frames) - 1)
    output_index = 1
    write_frame(output_dir / f"{output_index:08d}.png", first)
    started = time.time()

    prev = read_frame(frames[0], device, half, pad)
    for index in range(1, len(frames)):
        current = read_frame(frames[index], device, half, pad)
        for step in range(1, args.multi):
            timestep = step / args.multi
            middle = infer(prev, current, timestep)
            output_index += 1
            write_frame(
                output_dir / f"{output_index:08d}.png",
                to_image(middle, height, width),
            )
        output_index += 1
        write_frame(
            output_dir / f"{output_index:08d}.png",
            to_image(current, height, width),
        )
        prev = current
        if progress_file is not None:
            progress_file.write_text(
                f"{index}/{total_pairs}", encoding="utf-8"
            )
        if index % 10 == 0 or index == len(frames) - 1:
            print(
                f"PROGRESS {index}/{total_pairs} "
                f"({time.time() - started:.1f}s)",
                flush=True,
            )

    expected = len(frames) * args.multi
    duplicate_src = output_dir / f"{output_index:08d}.png"
    while output_index < expected:
        output_index += 1
        shutil.copyfile(
            duplicate_src, output_dir / f"{output_index:08d}.png"
        )

    print(
        f"DONE frames={output_index} expected={expected} "
        f"elapsed={time.time() - started:.1f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise SystemExit(1)
