"""设置对话框（S2：保存到 %APPDATA%/NEX/config.json）。"""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    LineEdit,
    MessageBoxBase,
    PushButton,
    SubtitleLabel,
)

from .. import APP_VERSION
from ..app_config import AppConfig
from .widgets import make_spin_box

ENCODERS = ["auto", "x264", "nvenc"]
ENCODER_LABELS = [
    "自动（推荐）",
    "软件编码 x264（兼容）",
    "硬件编码 NVENC（需驱动 610+）",
]


class SettingsDialog(MessageBoxBase):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config

        self.titleLabel = SubtitleLabel("设置", self)
        self.viewLayout.addWidget(self.titleLabel)

        form_host = QWidget(self)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.outEdit = LineEdit(form_host)
        self.outEdit.setText(config.output_dir)
        self.outEdit.setPlaceholderText("默认：源视频同目录")
        browse_btn = PushButton(form_host)
        browse_btn.setText("浏览...")
        browse_btn.clicked.connect(self._choose_output_dir)
        out_row = QWidget(form_host)
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.setSpacing(8)
        out_layout.addWidget(self.outEdit, 1)
        out_layout.addWidget(browse_btn)
        form.addRow(BodyLabel("默认输出目录", form_host), out_row)

        self.encoderBox = ComboBox(form_host)
        self.encoderBox.addItems(ENCODER_LABELS)
        self.encoderBox.setCurrentIndex(
            ENCODERS.index(config.encoder) if config.encoder in ENCODERS else 0
        )
        form.addRow(BodyLabel("视频编码器", form_host), self.encoderBox)

        self.gpuBox = ComboBox(form_host)
        self.gpuBox.addItems([f"GPU {config.gpu_id}（自动）"])
        form.addRow(BodyLabel("显卡选择", form_host), self.gpuBox)

        self.daysBox = make_spin_box(
            form_host, 1, 365, config.log_keep_days
        )
        form.addRow(BodyLabel("日志保留天数", form_host), self.daysBox)

        self.tempBox = make_spin_box(
            form_host, 0, 100, int(round(config.temp_limit))
        )
        form.addRow(BodyLabel("温度保护上限 (°C)", form_host), self.tempBox)

        self.viewLayout.addWidget(form_host)

        about = CaptionLabel(
            f"版本 {APP_VERSION} · 开源组件：Real-ESRGAN（BSD-3）、RIFE（MIT）、"
            "FFmpeg（GPL v3）、PySide6（LGPLv3）、qfluentwidgets（MIT）\n"
            "许可证文本见安装目录 licenses/。温度保护上限设为 0 表示关闭。",
            self,
        )
        about.setStyleSheet("color: #6B7280;")
        self.viewLayout.addWidget(about)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(560)

    def _choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择默认输出文件夹")
        if path:
            self.outEdit.setText(path)

    def accept(self) -> None:
        self.config.output_dir = self.outEdit.text().strip()
        index = self.encoderBox.currentIndex()
        self.config.encoder = ENCODERS[index] if 0 <= index < len(ENCODERS) else "auto"
        self.config.log_keep_days = self.daysBox.value()
        self.config.temp_limit = float(self.tempBox.value())
        self.config.save()
        super().accept()
