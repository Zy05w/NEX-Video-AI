"""添加任务对话框（原生 Qt）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from .. import engines
from ..i18n import t
from .base_dialog import BaseDialog

SR_MODELS = [
    ("动漫视频（推荐）", "realesr-animevideov3"),
    ("写实通用", "realesrgan-x4plus"),
    ("动漫插画", "realesrgan-x4plus-anime"),
]
RESOLUTIONS = ["2x", "3x", "4x", "1080p", "2K", "4K"]
FI_MODELS = [
    ("rife-v4.6（推荐）", "rife-v4.6"),
    ("rife-anime（动漫）", "rife-anime"),
    ("rife-HD", "rife-HD"),
    ("rife-UHD", "rife-UHD"),
    ("RIFE 4.25（PyTorch，需额外环境）", "practical-rife-4.25"),
]
FPS_OPTIONS = ["2x", "4x", "60", "120"]


@dataclass
class NewTaskRequest:
    files: list[str] = field(default_factory=list)
    output_dir: str = ""
    sr_enabled: bool = True
    sr_model: str = "realesr-animevideov3"
    sr_scale: int | None = 2
    sr_height: int | None = None
    fi_enabled: bool = True
    fi_model: str = "rife-v4.6"
    fi_mult: int | None = 2
    fi_fps: float | None = None
    start_now: bool = True


class AddTaskDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(t("添加任务"), parent)
        self.request: NewTaskRequest | None = None
        self._files: list[str] = []
        self.setMinimumWidth(680)

        form_host = QWidget(self)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 视频文件
        self.fileEdit = QLineEdit(form_host)
        self.fileEdit.setReadOnly(True)
        self.fileEdit.setPlaceholderText(t("尚未选择视频文件"))
        choose_btn = QPushButton(t("选择视频..."), form_host)
        choose_btn.clicked.connect(self._choose_files)
        file_row = QWidget(form_host)
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        file_layout.addWidget(self.fileEdit, 1)
        file_layout.addWidget(choose_btn)
        form.addRow(QLabel(t("视频文件"), form_host), file_row)

        # 输出位置
        self.outEdit = QLineEdit(form_host)
        self.outEdit.setPlaceholderText(t("默认：源视频同目录"))
        browse_btn = QPushButton(t("浏览..."), form_host)
        browse_btn.clicked.connect(self._choose_output_dir)
        out_row = QWidget(form_host)
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.setSpacing(8)
        out_layout.addWidget(self.outEdit, 1)
        out_layout.addWidget(browse_btn)
        form.addRow(QLabel(t("输出位置"), form_host), out_row)

        # AI 超分
        self.srSwitch = QCheckBox(t("启用"), form_host)
        self.srSwitch.setChecked(True)
        self.srModel = QComboBox(form_host)
        self.srModel.addItems([t(text) for text, _ in SR_MODELS])
        self.srRes = QComboBox(form_host)
        self.srRes.addItems(RESOLUTIONS)
        self.srRes.setCurrentIndex(0)
        sr_row = QWidget(form_host)
        sr_layout = QHBoxLayout(sr_row)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setSpacing(8)
        sr_layout.addWidget(self.srSwitch)
        sr_layout.addWidget(self.srModel, 1)
        sr_layout.addWidget(self.srRes)
        form.addRow(QLabel(t("AI 超分"), form_host), sr_row)

        # AI 补帧
        self.fiSwitch = QCheckBox(t("启用"), form_host)
        self.fiSwitch.setChecked(True)
        self.fiModel = QComboBox(form_host)
        pt_missing = bool(engines.check_practical_rife())
        self._fi_models = [
            (label, value)
            for label, value in FI_MODELS
            if value != engines.PRACTICAL_RIFE_MODEL or not pt_missing
        ]
        self.fiModel.addItems([t(text) for text, _ in self._fi_models])
        self.fiFps = QComboBox(form_host)
        self.fiFps.addItems(FPS_OPTIONS)
        self.fiFps.setCurrentIndex(0)
        fi_row = QWidget(form_host)
        fi_layout = QHBoxLayout(fi_row)
        fi_layout.setContentsMargins(0, 0, 0, 0)
        fi_layout.setSpacing(8)
        fi_layout.addWidget(self.fiSwitch)
        fi_layout.addWidget(self.fiModel, 1)
        fi_layout.addWidget(self.fiFps)
        form.addRow(QLabel(t("AI 补帧"), form_host), fi_row)

        self.srSwitch.toggled.connect(
            lambda on: (self.srModel.setEnabled(on), self.srRes.setEnabled(on))
        )
        self.fiSwitch.toggled.connect(
            lambda on: (self.fiModel.setEnabled(on), self.fiFps.setEnabled(on))
        )

        self.startCheck = QCheckBox(t("添加后立即开始"), form_host)
        self.startCheck.setChecked(True)
        form.addRow(QLabel("", form_host), self.startCheck)

        self.contentLayout.addWidget(form_host)

        self.errorLabel = QLabel("", self)
        self.errorLabel.setObjectName("errorLabel")
        self.errorLabel.setWordWrap(True)
        self.errorLabel.hide()
        self.contentLayout.addWidget(self.errorLabel)

        self.okButton.setText(t("添加"))
        self.cancelButton.setText(t("取消"))

    # ---------- 事件 ----------
    def _choose_files(self) -> None:
        video_filter = t(
            "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v)"
            ";;所有文件 (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self, t("选择视频文件"), "", video_filter
        )
        if not files:
            return
        self._files = files
        if len(files) == 1:
            self.fileEdit.setText(files[0])
        else:
            self.fileEdit.setText(
                t("已选择 {count} 个文件", count=len(files))
            )
        self.errorLabel.hide()

    def _choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t("选择输出文件夹"))
        if path:
            self.outEdit.setText(path)

    def validate(self) -> bool:
        if not self._files:
            self._show_error(t("请先选择要处理的视频文件"))
            return False
        if not self.srSwitch.isChecked() and not self.fiSwitch.isChecked():
            self._show_error(t("请至少开启“超分”或“补帧”中的一项"))
            return False
        self.errorLabel.hide()
        return True

    def accept(self) -> None:
        if not self.validate():
            return
        resolution = self.srRes.currentText()
        if resolution in ("2x", "3x", "4x"):
            sr_scale, sr_height = int(resolution[0]), None
        else:
            sr_scale, sr_height = None, {"1080p": 1080, "2K": 1440, "4K": 2160}[resolution]

        fps_text = self.fiFps.currentText()
        if fps_text in ("2x", "4x"):
            fi_mult, fi_fps = int(fps_text[0]), None
        else:
            fi_mult, fi_fps = None, float(fps_text)

        self.request = NewTaskRequest(
            files=list(self._files),
            output_dir=self.outEdit.text().strip(),
            sr_enabled=self.srSwitch.isChecked(),
            sr_model=SR_MODELS[self.srModel.currentIndex()][1],
            sr_scale=sr_scale,
            sr_height=sr_height,
            fi_enabled=self.fiSwitch.isChecked(),
            fi_model=self._fi_models[self.fiModel.currentIndex()][1],
            fi_mult=fi_mult,
            fi_fps=fi_fps,
            start_now=self.startCheck.isChecked(),
        )
        super().accept()

    def _show_error(self, text: str) -> None:
        self.errorLabel.setText(text)
        self.errorLabel.show()
