"""S7 管线集成测试：磁盘预检与中间帧清理。"""

from pathlib import Path

import pytest

from nex import pipeline, storage
from nex.engines import MediaInfo
from nex.pipeline import PipelineError, PipelineOptions, SROptions, FIOptions


class FakeLogger:
    def __init__(self, task_id, on_line=None):
        self.path = Path(pipeline.tempfile.gettempdir()) / "nex_test.log"
        self.lines = []

    def log(self, stage, message):
        self.lines.append((stage, message))

    def close(self):
        pass


INFO = MediaInfo(
    path=Path("sample.mp4"),
    duration=2.0,
    fps=24.0,
    width=320,
    height=180,
    video_codec="h264",
    audio_codec=None,
)


def _prepare(monkeypatch, tmp_path):
    source = tmp_path / "sample.mp4"
    source.write_bytes(b"x")
    info = MediaInfo(
        path=source,
        duration=INFO.duration,
        fps=INFO.fps,
        width=INFO.width,
        height=INFO.height,
        video_codec=INFO.video_codec,
        audio_codec=None,
    )
    monkeypatch.setattr(pipeline.engines, "check_engines", lambda: [])
    monkeypatch.setattr(pipeline.engines, "probe", lambda path: info)
    monkeypatch.setattr(pipeline, "TaskLogger", FakeLogger)
    monkeypatch.setattr(pipeline.storage, "ensure_writable", lambda path: None)
    return source


def test_pipeline_stops_before_extract_when_disk_is_low(
    monkeypatch, tmp_path
):
    source = _prepare(monkeypatch, tmp_path)
    called = {"extract": False}

    def fake_extract(*args, **kwargs):
        called["extract"] = True
        return 0

    monkeypatch.setattr(pipeline.engines, "extract_frames", fake_extract)
    monkeypatch.setattr(
        pipeline.storage,
        "check_disk_space",
        lambda *args, **kwargs: [
            storage.DiskSpaceIssue(
                kind="temp",
                path=tmp_path,
                required=10 * 1024**3,
                available=1 * 1024**3,
            )
        ],
    )
    with pytest.raises(PipelineError) as excinfo:
        pipeline.run_pipeline(
            PipelineOptions(
                input_path=source,
                output_dir=tmp_path,
                sr=SROptions(
                    enabled=True, model="realesr-animevideov3", scale=2
                ),
                temp_guard=False,
            )
        )
    assert "磁盘空间不足" in str(excinfo.value)
    assert called["extract"] is False


def test_pipeline_removes_intermediate_frames(monkeypatch, tmp_path):
    source = _prepare(monkeypatch, tmp_path)
    created: dict[str, Path] = {}

    def fake_extract(input_path, frames_dir, info, log_path, cancel, on_progress=None):
        frames_dir.mkdir(parents=True)
        (frames_dir / "00000001.png").write_bytes(b"x")
        created["in"] = frames_dir
        return 1

    def fake_sr(input_dir, output_dir, *args, **kwargs):
        output_dir.mkdir(parents=True)
        (output_dir / "00000001.png").write_bytes(b"x")
        created["sr"] = output_dir
        return 1

    def fake_fi(input_dir, output_dir, *args, **kwargs):
        output_dir.mkdir(parents=True)
        (output_dir / "00000001.png").write_bytes(b"x")
        created["fi"] = output_dir
        return 1

    during_encode = {}

    def fake_encode(**kwargs):
        during_encode["in_gone"] = not created["in"].exists()
        during_encode["sr_gone"] = not created["sr"].exists()
        during_encode["fi_present"] = created["fi"].exists()
        kwargs["output_path"].write_bytes(b"video")

    monkeypatch.setattr(pipeline.engines, "extract_frames", fake_extract)
    monkeypatch.setattr(pipeline.engines, "run_sr", fake_sr)
    monkeypatch.setattr(pipeline.engines, "run_fi", fake_fi)
    monkeypatch.setattr(pipeline.engines, "encode_video", fake_encode)
    monkeypatch.setattr(pipeline.engines, "count_video_frames", lambda path: 2)

    result = pipeline.run_pipeline(
        PipelineOptions(
            input_path=source,
            output_dir=tmp_path,
            sr=SROptions(
                enabled=True, model="realesr-animevideov3", scale=2
            ),
            fi=FIOptions(enabled=True, model="rife-v4.6", multiplier=2),
            temp_guard=False,
        )
    )
    assert during_encode == {
        "in_gone": True,
        "sr_gone": True,
        "fi_present": True,
    }
    assert result.output_path.exists()
    assert created["in"].exists() is False
    assert created["sr"].exists() is False
    assert created["fi"].exists() is False
