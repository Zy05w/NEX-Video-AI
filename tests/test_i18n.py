"""语言切换与翻译测试。"""

from nex import i18n
from nex.task import TaskParams


def test_english_basic_translations():
    i18n.set_language("en")
    try:
        assert i18n.t("添加任务") == "Add Task"
        assert i18n.t("等待中") == "Pending"
        assert (
            i18n.t("已添加 {count} 个任务", count=2)
            == "Added 2 task(s)"
        )
        params = TaskParams(
            input_path="a.mp4",
            sr_scale=None,
            sr_height=None,
            fi_mult=None,
            fi_fps=None,
        )
        assert params.summary() == "Upscaling / Interpolation"
    finally:
        i18n.set_language("zh")


def test_chinese_is_default_and_unchanged():
    i18n.set_language("zh")
    assert i18n.t("添加任务") == "添加任务"
    params = TaskParams(input_path="a.mp4", sr_scale=2, fi_mult=2)
    assert params.summary() == "2x / 2x"


def test_logger_stage_translated(tmp_path):
    from nex.logger import TaskLogger

    i18n.set_language("en")
    try:
        logger = TaskLogger("abc", log_dir=tmp_path)
        logger.log("抽帧", "started")
        logger.close()
        text = (tmp_path / "abc.log").read_text(encoding="utf-8")
        assert "[Extract] started" in text
    finally:
        i18n.set_language("zh")


def test_tutorial_english_content():
    from nex.ui.tutorial import TUTORIAL_MARKDOWN_EN

    assert "Quick Start" in TUTORIAL_MARKDOWN_EN
    assert "AI Upscaling" in TUTORIAL_MARKDOWN_EN
    assert "rife-v4.6" in TUTORIAL_MARKDOWN_EN
