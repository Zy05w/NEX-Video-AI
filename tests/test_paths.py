"""Windows 超长路径辅助函数测试（S7）。"""

import os
from pathlib import Path

import pytest

from nex import paths


def test_short_path_is_not_rewritten():
    if os.name != "nt":
        pytest.skip("Windows only")
    assert paths.extended_path("C:\\temp\\a.mp4") == "C:\\temp\\a.mp4"


def test_long_drive_path_gets_extended_prefix():
    if os.name != "nt":
        pytest.skip("Windows only")
    long_path = "D:\\" + os.sep.join(["abcdefgh"] * 40) + "\\a.mp4"
    assert paths.extended_path(long_path).startswith("\\\\?\\D:\\")


def test_long_unc_path_gets_unc_prefix():
    if os.name != "nt":
        pytest.skip("Windows only")
    long_path = "\\\\server\\share\\" + os.sep.join(["abcdefgh"] * 40) + "\\a.mp4"
    assert paths.extended_path(long_path).startswith("\\\\?\\UNC\\server\\share\\")


def test_already_extended_path_is_unchanged():
    if os.name != "nt":
        pytest.skip("Windows only")
    value = "\\\\?\\D:\\" + os.sep.join(["abcdefgh"] * 40) + "\\a.mp4"
    assert paths.extended_path(value) == value


def test_path_exists_handles_long_chinese_path(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows only")
    folder = tmp_path
    for index in range(30):
        folder = folder / f"子目录{index:02d}abcdef"
    folder.mkdir(parents=True)
    target = folder / "测试视频 超长路径.mp4"
    target.write_bytes(b"x")
    assert len(str(target)) > 260
    assert paths.exists(target)
    assert paths.is_file(target)
    assert paths.file_size(target) == 1


def test_write_probe_works_for_long_path(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows only")
    folder = tmp_path
    for index in range(30):
        folder = folder / f"子目录{index:02d}abcdef"
    paths.write_probe(folder)
    assert not any(folder.glob(".nex_write_test*"))


def test_resource_path_points_to_icon():
    assert paths.resource_path("nex.ico").exists()
