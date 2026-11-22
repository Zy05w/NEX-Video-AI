"""关于页内容测试（S7）。"""

from nex.ui.about_dialog import LICENSE_ITEMS


def test_about_lists_all_shipped_components():
    names = " ".join(name for name, _ in LICENSE_ITEMS)
    for component in (
        "Real-ESRGAN",
        "RIFE",
        "Practical-RIFE",
        "FFmpeg",
        "PySide6",
        "Python",
        "PyInstaller",
    ):
        assert component in names


def test_about_licenses_match_compliance_docs():
    mapping = dict(LICENSE_ITEMS)
    assert mapping["FFmpeg"] == "GPL v3"
    assert mapping["PySide6 / Qt"] == "LGPLv3"
    assert mapping["Real-ESRGAN / ncnn"] == "BSD-3-Clause"
