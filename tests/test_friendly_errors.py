"""友好错误信息测试（S7）。"""

from nex import errors


def test_disk_full_oserror_is_explained():
    message = errors.friendly_os_error(OSError(28, "No space left on device"))
    assert "磁盘空间不足" in message


def test_windows_disk_full_winerror_is_explained():
    exc = OSError(28, "There is not enough space on the disk")
    exc.winerror = 112
    assert "磁盘空间不足" in errors.friendly_os_error(exc)


def test_permission_error_is_explained():
    exc = PermissionError(13, "Access is denied")
    exc.winerror = 5
    message = errors.friendly_os_error(exc, path="D:\\out")
    assert "没有权限" in message
    assert "D:\\out" in message


def test_long_path_error_is_explained():
    exc = OSError(206, "The filename or extension is too long")
    assert "路径过长" in errors.friendly_os_error(exc)


def test_generic_oserror_includes_message():
    message = errors.friendly_os_error(OSError(999, "weird failure"))
    assert "weird failure" in message


def test_diagnose_engine_log_detects_disk_full():
    assert "磁盘空间不足" in errors.diagnose_engine_log(
        "av_interleaved_write_frame(): No space left on device"
    )


def test_diagnose_engine_log_detects_permission():
    assert "没有权限" in errors.diagnose_engine_log(
        "Error opening output file: Permission denied"
    )


def test_diagnose_engine_log_detects_corrupt_video():
    assert "损坏" in errors.diagnose_engine_log(
        "moov atom not found\nInvalid data found when processing input"
    )


def test_diagnose_engine_log_detects_missing_file_before_corrupt():
    assert "找不到" in errors.diagnose_engine_log(
        "Error opening input: No such file or directory"
    )


def test_diagnose_engine_log_returns_none_for_unknown():
    assert errors.diagnose_engine_log("some unrelated engine output") is None
