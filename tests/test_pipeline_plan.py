"""管线规划逻辑单元测试（S3）。"""

from pathlib import Path

import pytest

from nex.engines import MediaInfo
from nex.pipeline import (
    FIOptions,
    PipelineError,
    SROptions,
    _even,
    _plan_fi,
    _plan_sr,
)

INFO = MediaInfo(
    path=Path("sample.mp4"),
    duration=3.0,
    fps=24.0,
    width=640,
    height=360,
    video_codec="h264",
    audio_codec="aac",
)


def test_even_rounds_down_and_keeps_minimum():
    assert _even(1280) == 1280
    assert _even(1279) == 1278
    assert _even(1) == 2


def test_sr_multiplier_2x():
    plan = _plan_sr(
        SROptions(enabled=True, model="realesr-animevideov3", scale=2), INFO
    )
    assert plan["skip"] is False
    assert plan["scale"] == 2
    assert (plan["final_w"], plan["final_h"]) == (1280, 720)


def test_sr_target_height_1080_uses_3x():
    plan = _plan_sr(SROptions(enabled=True, target_height=1080), INFO)
    assert plan["skip"] is False
    assert plan["scale"] == 3
    assert (plan["final_w"], plan["final_h"]) == (1920, 1080)


def test_sr_x4_only_model_runs_4x_then_downscales_to_2x():
    plan = _plan_sr(
        SROptions(enabled=True, model="realesrgan-x4plus", scale=2), INFO
    )
    assert plan["scale"] == 4
    assert (plan["final_w"], plan["final_h"]) == (1280, 720)


def test_sr_skips_when_target_not_larger():
    plan = _plan_sr(SROptions(enabled=True, target_height=240), INFO)
    assert plan["skip"] is True
    assert plan["final_h"] == 240


def test_sr_rejects_unknown_model():
    with pytest.raises(PipelineError):
        _plan_sr(SROptions(enabled=True, model="unknown-model"), INFO)


def test_fi_multiplier():
    passes, fps, _ = _plan_fi(FIOptions(enabled=True, multiplier=2), INFO)
    assert passes == 1 and fps == 48.0
    passes, fps, _ = _plan_fi(FIOptions(enabled=True, multiplier=4), INFO)
    assert passes == 2 and fps == 96.0


def test_fi_target_60_from_24_uses_two_passes():
    passes, fps, _ = _plan_fi(FIOptions(enabled=True, target_fps=60), INFO)
    assert passes == 2
    assert fps == 60.0


def test_fi_target_120_from_24_uses_three_passes():
    passes, fps, _ = _plan_fi(FIOptions(enabled=True, target_fps=120), INFO)
    assert passes == 3
    assert fps == 120.0


def test_fi_target_30_from_24_uses_one_pass():
    passes, fps, _ = _plan_fi(FIOptions(enabled=True, target_fps=30), INFO)
    assert passes == 1
    assert fps == 30.0


def test_fi_target_not_above_source_is_skipped():
    passes, fps, note = _plan_fi(FIOptions(enabled=True, target_fps=20), INFO)
    assert passes == 0
    assert fps == 24.0
    assert "跳过" in note


def test_fi_rejects_conflicting_options():
    with pytest.raises(PipelineError):
        _plan_fi(FIOptions(enabled=True, multiplier=2, target_fps=60), INFO)


def test_fi_accepts_practical_rife_model():
    from nex import engines

    passes, fps, _ = _plan_fi(
        FIOptions(
            enabled=True,
            model=engines.PRACTICAL_RIFE_MODEL,
            multiplier=2,
        ),
        INFO,
    )
    assert passes == 1
    assert fps == 48.0
