"""添加任务对话框（S2：表单与假数据录入）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    LineEdit,
    MessageBoxBase,
    PushButton,
    SubtitleLabel,
    SwitchButton,
)

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
]
FPS_OPTIONS = ["2x", "4x", "60", "120"]

VIDEO_FILTER = (
    "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v);;所有文件 (*.*)"
)


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


class AddTaskDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.request: NewTaskRequest | None = None
        self._files: list[str] = []

        self.titleLabel = SubtitleLabel("添加任务", self)
        self.viewLayout.addWidget(self.titleLabel)

        form_host = QWidget(self)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # 视频文件
        self.fileEdit = LineEdit(form_host)
        self.fileEdit.setReadOnly(True)
        self.fileEdit.setPlaceholderText("尚未选择视频文件")
        choose_btn = PushButton(form_host)
        choose_btn.setText("选择视频...")
        choose_btn.clicked.connect(self._choose_files)
        file_row = QWidget(form_host)
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        file_layout.addWidget(self.fileEdit, 1)
        file_layout.addWidget(choose_btn)
        form.addRow(BodyLabel("视频文件", form_host), file_row)

        # 输出位置
        self.outEdit = LineEdit(form_host)
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
        form.addRow(BodyLabel("输出位置", form_host), out_row)

        # AI 超分
        self.srSwitch = SwitchButton(form_host)
        self.srSwitch.setChecked(True)
        self.srModel = ComboBox(form_host)
        self.srModel.addItems([text for text, _ in SR_MODELS])
        self.srRes = ComboBox(form_host)
        self.srRes.addItems(RESOLUTIONS)
        self.srRes.setCurrentIndex(0)
        sr_row = QWidget(form_host)
        sr_layout = QHBoxLayout(sr_row)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setSpacing(8)
        sr_layout.addWidget(self.srSwitch)
        sr_layout.addWidget(self.srModel, 1)
        sr_layout.addWidget(self.srRes)
        form.addRow(BodyLabel("AI 超分", form_host), sr_row)

        # AI 补帧
        self.fiSwitch = SwitchButton(form_host)
        self.fiSwitch.setChecked(True)
        self.fiModel = ComboBox(form_host)
        self.fiModel.addItems([text for text, _ in FI_MODELS])
        self.fiFps = ComboBox(form_host)
        self.fiFps.addItems(FPS_OPTIONS)
        self.fiFps.setCurrentIndex(0)
        fi_row = QWidget(form_host)
        fi_layout = QHBoxLayout(fi_row)
        fi_layout.setContentsMargins(0, 0, 0, 0)
        fi_layout.setSpacing(8)
        fi_layout.addWidget(self.fiSwitch)
        fi_layout.addWidget(self.fiModel, 1)
        fi_layout.addWidget(self.fiFps)
        form.addRow(BodyLabel("AI 补帧", form_host), fi_row)

        self.srSwitch.checkedChanged.connect(
            lambda on: (self.srModel.setEnabled(on), self.srRes.setEnabled(on))
        )
        self.fiSwitch.checkedChanged.connect(
            lambda on: (self.fiModel.setEnabled(on), self.fiFps.setEnabled(on))
        )

        self.startCheck = CheckBox(form_host)
        self.startCheck.setText("添加后立即开始")
        self.startCheck.setChecked(True)
        form.addRow(BodyLabel("", form_host), self.startCheck)

        self.viewLayout.addWidget(form_host)

        self.errorLabel = CaptionLabel("", self)
        self.errorLabel.setStyleSheet("color: #E5484D;")
        self.errorLabel.setVisible(False)
        self.viewLayout.addWidget(self.errorLabel)

        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(640)

    # ---------- 事件 ----------
    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "", VIDEO_FILTER
        )
        if not files:
            return
        self._files = files
        if len(files) == 1:
            self.fileEdit.setText(files[0])
        else:
            self.fileEdit.setText(f"已选择 {len(files)} 个文件")
        self.errorLabel.setVisible(False)

    def _choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.outEdit.setText(path)

    def validate(self) -> bool:
        if not self._files:
            self._show_error("请先选择要处理的视频文件")
            return False
        if not self.srSwitch.isChecked() and not self.fiSwitch.isChecked():
            self._show_error("请至少开启“超分”或“补帧”中的一项")
            return False
        self.errorLabel.setVisible(False)
        return True

    def accept(self) -> None:
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
            fi_model=FI_MODELS[self.fiModel.currentIndex()][1],
            fi_mult=fi_mult,
            fi_fps=fi_fps,
            start_now=self.startCheck.isChecked(),
        )
        super().accept()

    def _show_error(self, text: str) -> None:
        self.errorLabel.setText(text)
        self.errorLabel.setVisible(True)
