"""内置使用教程对话框。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QTextCursor
from qfluentwidgets import MessageBoxBase, SubtitleLabel, TextEdit

from ..i18n import get_language, t

TUTORIAL_MARKDOWN = """
# NEX 视频增强 · 使用教程

## 1. 快速上手

1. 点击右上角「添加任务」
2. 选择要处理的视频（可多选，也可以直接把视频拖进窗口）
3. 按需设置超分、补帧和输出位置
4. 点击「添加」；勾选「添加后立即开始」会自动处理
5. 处理完成后，在原视频所在目录找到文件名带 `_NEX` 的新视频

> 建议先用 10~30 秒的短视频测试参数，满意后再处理长视频。

## 2. AI 超分（画面更清晰、更大）

- 动漫视频：选择「动漫视频（推荐）」
- 真人视频：选择「写实通用」
- 动漫插画/图片风：选择「动漫插画」
- 分辨率：
  - `2x / 3x / 4x`：按倍数放大
  - `1080p / 2K / 4K`：按目标清晰度输出
- 超分比较耗时，4K 输出更慢，请耐心等待

## 3. AI 补帧（画面更流畅）

- 推荐模型：`rife-v4.6`
- `2x / 4x`：帧率翻倍 / 四倍
- `60 / 120`：直接指定目标帧率（例如 24fps 视频选 60，会自动插值到 60fps）
- 动漫视频也可以选择 `rife-anime`

## 4. 任务队列

- 任务会按顺序逐个处理（显卡一次只做一件事，更稳定）
- 等待中：可以取消
- 处理中：可以取消；取消后可以重试
- 失败 / 已取消：可以重试或删除记录
- 删除只删除记录，不会删除视频文件
- 关闭软件再打开，任务记录会保留；处理中的任务会恢复为等待中

## 5. 日志与设置

- 底部日志面板显示当前选中任务的详细进度
- 设置中可以修改：默认输出目录、编码器、显卡、日志保留天数、温度保护上限
- 温度保护：处理中每 5 秒检查一次显卡温度，超过上限（默认 88°C）会自动安全停止任务
- 温度保护上限设为 0 表示关闭

## 6. 常见问题

- **处理很慢？** AI 处理比普通转码慢很多，属于正常现象，4K 更慢
- **提示显存不足？** 降低分辨率/超分倍数，或先只做补帧再试
- **输出在哪里？** 默认在原视频同目录，文件名带 `_NEX`
- **支持哪些格式？** mp4 / mkv / mov / avi / webm 等常见格式
- **处理时可以关闭软件吗？** 建议先取消任务再关闭；直接关闭会停止当前任务
- **会损伤显卡吗？** AI 计算属于正常负载，不超频、不改电压；软件还有温度保护
- **没有声音？** 软件会尽量复制原音频；请确认原视频本身有音轨
- **视频编码很慢？** 当前默认使用 x264 软件编码；NVENC 需显卡驱动 610+

## 7. 使用建议

- 处理长视频时保持电源接通、机身通风良好
- 重要视频先备份原文件
- 每完成一批重要修改，可以双击项目目录里的「备份项目.bat」做本地备份

---
版本 0.1.0 · 如需更详细说明，请查看项目 docs 目录
"""

TUTORIAL_MARKDOWN_EN = """
# NEX Video Enhancer · User Guide

## 1. Quick Start

1. Click **Add Task** at the top right
2. Choose one or more videos (or drag them into the window)
3. Set upscaling, frame interpolation and output folder as needed
4. Click **Add**; enable **Start immediately after adding** to begin
5. When finished, find the new file ending with `_NEX` in the source folder

> Start with a 10–30 second clip before processing long videos.

## 2. AI Upscaling

- Anime video: **Anime Video (Recommended)**
- Live action: **Realistic / General**
- Anime illustration: **Anime Illustration**
- Resolution:
  - `2x / 3x / 4x`: scale factor
  - `1080p / 2K / 4K`: target quality
- Upscaling is slow; 4K output takes longer

## 3. AI Frame Interpolation

- Recommended model: `rife-v4.6` (included in the bundled ncnn package)
- `2x / 4x`: double / quadruple the frame rate
- `60 / 120`: target frame rate (e.g. 24fps → 60fps)
- Anime videos can use `rife-anime`

## 4. Task Queue

- Tasks are processed one at a time for GPU stability
- Pending: can cancel
- Processing: can cancel; retry after cancellation
- Failed / Cancelled: retry or delete the record
- Deleting a record never deletes the video file
- Records survive restart; running tasks return to Pending

## 5. Logs & Settings

- The log panel shows details for the selected task
- Settings: default output folder, encoder, GPU, log retention, temperature limit, language
- Temperature guard checks the GPU every 5 seconds and stops safely above the limit (default 88°C)
- Set the temperature limit to 0 to disable it

## 6. FAQ

- **Slow?** AI processing is much slower than transcoding; 4K is slower
- **Out of VRAM?** Lower the resolution/scale, or disable interpolation
- **Where is the output?** Same folder as the source, filename ends with `_NEX`
- **Supported formats?** mp4 / mkv / mov / avi / webm and other common formats
- **Close while processing?** Cancel first; closing stops the current task
- **GPU safety?** Normal compute load, no overclocking; a temperature guard is included
- **No audio?** The app copies source audio when possible; check the source file
- **Encoding slow?** x264 software encoding is used by default; NVENC requires driver 610+
- **Language?** Change it in Settings, then restart the app to apply

## 7. Tips

- Keep the laptop plugged in and well ventilated for long jobs
- Back up important source videos first
- Use the project backup script regularly

---
Version 0.1.0 · For more details, see the project docs folder
"""


class TutorialDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(t("使用教程"), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.textEdit = TextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setFont(QFont("Microsoft YaHei UI", 10))
        markdown = (
            TUTORIAL_MARKDOWN_EN
            if get_language() == "en"
            else TUTORIAL_MARKDOWN
        )
        self.textEdit.setMarkdown(markdown)
        self.textEdit.selectAll()
        self.textEdit.setTextColor(QColor("#1F2329"))
        self.textEdit.moveCursor(QTextCursor.Start)
        self.textEdit.setMinimumSize(720, 500)
        self.textEdit.setStyleSheet(
            "QTextEdit { background: #FFFFFF; color: #1F2329;"
            " border: 1px solid #E5EAF2; border-radius: 8px; padding: 8px; }"
        )
        self.viewLayout.addWidget(self.textEdit)

        self.yesButton.setText(t("知道了"))
        self.hideCancelButton()
        self.widget.setMinimumSize(780, 620)
