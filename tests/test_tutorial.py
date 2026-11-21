"""内置教程内容完整性测试。"""

from nex.ui.tutorial import TUTORIAL_MARKDOWN


def test_tutorial_has_key_sections():
    for title in (
        "快速上手",
        "AI 超分",
        "AI 补帧",
        "任务队列",
        "日志与设置",
        "常见问题",
    ):
        assert title in TUTORIAL_MARKDOWN


def test_tutorial_mentions_safety_and_output():
    assert "温度保护" in TUTORIAL_MARKDOWN
    assert "_NEX" in TUTORIAL_MARKDOWN
    assert "显卡" in TUTORIAL_MARKDOWN
