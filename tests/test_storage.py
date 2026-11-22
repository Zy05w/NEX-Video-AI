"""磁盘空间预检测试（S7）。"""

from collections import namedtuple
from pathlib import Path

import pytest

from nex import storage
from nex.engines import MediaInfo
from nex.pipeline import FIOptions, SROptions, _plan_fi, _plan_sr

INFO = MediaInfo(
    path=Path("sample.mp4"),
    duration=10.0,
    fps=24.0,
    width=640,
    height=360,
    video_codec="h264",
    audio_codec="aac",
)


def test_format_size_readable_units():
    assert storage.format_size(512) == "1 KB"
    assert storage.format_size(5 * 1024 * 1024) == "5 MB"
    assert storage.format_size(3 * 1024**3).endswith("GB")


def test_estimate_temp_bytes_is_positive_and_grows_with_stages():
    plain = storage.estimate_temp_bytes(INFO, None, 0)
    sr_plan = _plan_sr(
        SROptions(enabled=True, model="realesr-animevideov3", scale=2), INFO
    )
    passes, _, _ = _plan_fi(FIOptions(enabled=True, multiplier=2), INFO)
    with_sr = storage.estimate_temp_bytes(INFO, sr_plan, 0)
    with_both = storage.estimate_temp_bytes(INFO, sr_plan, passes)
    assert 0 < plain < with_sr < with_both


def test_staged_cleanup_peak_is_lower_than_keep_everything():
    sr_plan = _plan_sr(
        SROptions(enabled=True, model="realesr-animevideov3", scale=2), INFO
    )
    staged = storage.estimate_temp_bytes(INFO, sr_plan, 2, keep_temp=False)
    kept = storage.estimate_temp_bytes(INFO, sr_plan, 2, keep_temp=True)
    assert staged < kept


def test_estimate_output_bytes_scales_with_target():
    small = storage.estimate_output_bytes(
        INFO, 640, 360, 24.0, source_bytes=10 * 1024 * 1024
    )
    large = storage.estimate_output_bytes(
        INFO, 3840, 2160, 60.0, source_bytes=10 * 1024 * 1024
    )
    assert large > small > 0


def test_output_estimate_does_not_blow_up_for_large_source():
    movie = MediaInfo(
        path=Path("movie.mkv"),
        duration=2 * 3600,
        fps=24.0,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec="dts",
    )
    source = 50 * 1024**3  # 50GB 蓝光原盘
    estimate = storage.estimate_output_bytes(
        movie, 3840, 2160, 48.0, source_bytes=source
    )
    assert estimate < source * 2
    assert estimate > 10 * 1024**3


def test_check_disk_space_reports_insufficient(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "_free_bytes", lambda path: 10 * 1024**2)
    issues = storage.check_disk_space(
        tmp_path, 500 * 1024**2, tmp_path, 100 * 1024**2
    )
    assert issues
    assert "空间不足" in issues[0].message()
    assert "GB" in issues[0].message() or "MB" in issues[0].message()


def test_check_disk_space_passes_when_enough(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "_free_bytes", lambda path: 100 * 1024**3)
    assert (
        storage.check_disk_space(
            tmp_path, 500 * 1024**2, tmp_path, 100 * 1024**2
        )
        == []
    )


def test_same_drive_requirements_are_combined(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "_free_bytes", lambda path: 100 * 1024**2)
    monkeypatch.setattr(storage, "_drive", lambda path: "c:")
    issues = storage.check_disk_space(
        tmp_path, 60 * 1024**2, tmp_path, 60 * 1024**2
    )
    assert issues and issues[0].kind == "both"


def test_different_drives_are_checked_separately(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "_drive", lambda path: "c:" if "temp" in str(path) else "d:")
    monkeypatch.setattr(
        storage,
        "_free_bytes",
        lambda path: 200 * 1024**2 if "temp" in str(path) else 1024**3,
    )
    (tmp_path / "temp").mkdir()
    (tmp_path / "output").mkdir()
    issues = storage.check_disk_space(
        tmp_path / "temp", 60 * 1024**2, tmp_path / "output", 60 * 1024**2
    )
    assert issues == []


def test_ensure_writable_creates_and_removes_probe(tmp_path):
    target = tmp_path / "out"
    storage.ensure_writable(target)
    assert target.is_dir()
    assert not list(target.glob(".nex_write_test*"))
