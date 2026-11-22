"""设置对话框（原生 Qt）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from .. import APP_VERSION
from ..app_config import AppConfig
from ..i18n import LANGUAGE_LABELS, t
from .base_dialog import BaseDialog
from .tutorial import TutorialDialog
from .widgets import make_spin_box

ENCODERS = ["auto", "x264", "nvenc"]
ENCODER_LABELS = [
    "自动（推荐）",
    "软件编码 x264（兼容）",
    "硬件编码 NVENC（需驱动 610+）",
]


class SettingsDialog(BaseDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(t("设置"), parent)
        self.config = config
        self.setMinimumWidth(680)

        form_host = QWidget(self)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.outEdit = QLineEdit(form_host)
        self.outEdit.setText(config.output_dir)
        self.outEdit.setPlaceholderText(t("默认：源视频同目录"))
        browse_btn = QPushButton(t("浏览..."), form_host)
        browse_btn.clicked.connect(self._choose_output_dir)
        out_row = QWidget(form_host)
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.setSpacing(8)
        out_layout.addWidget(self.outEdit, 1)
        out_layout.addWidget(browse_btn)
        form.addRow(QLabel(t("默认输出目录"), form_host), out_row)

        self.encoderBox = QComboBox(form_host)
        self.encoderBox.addItems([t(label) for label in ENCODER_LABELS])
        self.encoderBox.setCurrentIndex(
            ENCODERS.index(config.encoder) if config.encoder in ENCODERS else 0
        )
        form.addRow(QLabel(t("视频编码器"), form_host), self.encoderBox)

        self.languageBox = QComboBox(form_host)
        self.languageBox.addItems(
            [LANGUAGE_LABELS["zh"], LANGUAGE_LABELS["en"]]
        )
        self.languageBox.setCurrentIndex(0 if config.language == "zh" else 1)
        form.addRow(QLabel(t("界面语言"), form_host), self.languageBox)

        self.gpuBox = QComboBox(form_host)
        self.gpuBox.addItems([t("GPU {id}（自动）", id=config.gpu_id)])
        form.addRow(QLabel(t("显卡选择"), form_host), self.gpuBox)

        self.daysBox = make_spin_box(form_host, 1, 365, config.log_keep_days)
        form.addRow(QLabel(t("日志保留天数"), form_host), self.daysBox)

        self.tempBox = make_spin_box(
            form_host, 0, 100, int(round(config.temp_limit))
        )
        form.addRow(QLabel(t("温度保护上限 (°C)"), form_host), self.tempBox)

        self.contentLayout.addWidget(form_host)

        tutorial_row = QWidget(self)
        tutorial_layout = QHBoxLayout(tutorial_row)
        tutorial_layout.setContentsMargins(0, 0, 0, 0)
        self.tutorialBtn = QPushButton(t("使用教程"), tutorial_row)
        self.tutorialBtn.clicked.connect(self._show_tutorial)
        tutorial_layout.addWidget(self.tutorialBtn)
        tutorial_layout.addStretch(1)
        self.contentLayout.addWidget(tutorial_row)

        about = QLabel(
            t(
                "版本 {version} · 开源组件：Real-ESRGAN（BSD-3）、RIFE（MIT）、"
                "FFmpeg（GPL v3）、PySide6（LGPLv3）\n"
                "许可证文本见安装目录 licenses/。温度保护上限设为 0 表示关闭。",
                version=APP_VERSION,
            ),
            self,
        )
        about.setWordWrap(True)
        about.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.contentLayout.addWidget(about)

        self.okButton.setText(t("保存"))
        self.cancelButton.setText(t("取消"))

    def _choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t("选择默认输出文件夹"))
        if path:
            self.outEdit.setText(path)

    def _show_tutorial(self) -> None:
        TutorialDialog(self).exec()

    def accept(self) -> None:
        self.config.output_dir = self.outEdit.text().strip()
        index = self.encoderBox.currentIndex()
        self.config.encoder = ENCODERS[index] if 0 <= index < len(ENCODERS) else "auto"
        self.config.log_keep_days = self.daysBox.value()
        self.config.temp_limit = float(self.tempBox.value())
        self.config.language = (
            "zh" if self.languageBox.currentIndex() == 0 else "en"
        )
        self.config.save()
        super().accept()
