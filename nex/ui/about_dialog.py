"""关于对话框：版本、开源组件与许可证入口。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, engines, paths
from ..i18n import t
from .base_dialog import BaseDialog

LICENSE_ITEMS = [
    ("Real-ESRGAN / ncnn", "BSD-3-Clause"),
    ("RIFE / rife-ncnn-vulkan", "MIT"),
    ("Practical-RIFE 4.25（可选）", "MIT"),
    ("FFmpeg", "GPL v3"),
    ("PySide6 / Qt", "LGPLv3"),
    ("Python", "PSF License"),
    ("PyInstaller", "GPL + 启动器例外"),
]


class AboutDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(t("关于 NEX"), parent, show_cancel=False)
        self.setMinimumWidth(640)
        self.okButton.setText(t("关闭"))

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        icon_path = paths.resource_path("nex.ico")
        icon_label = QLabel(header)
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(
                    56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        icon_label.setFixedSize(56, 56)
        header_layout.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        name = QLabel(t(APP_NAME), header)
        name.setObjectName("dialogTitle")
        version = QLabel(
            t("版本 {version}", version=APP_VERSION), header
        )
        version.setStyleSheet("color: #6B7280;")
        description = QLabel(t("AI 视频超分与补帧工具"), header)
        description.setStyleSheet("color: #6B7280;")
        title_box.addWidget(name)
        title_box.addWidget(version)
        title_box.addWidget(description)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)
        self.contentLayout.addWidget(header)

        intro = QLabel(t("本软件使用以下开源组件："), self)
        self.contentLayout.addWidget(intro)

        items = "<br>".join(
            f"· {t(name)} — {t(license_name)}"
            for name, license_name in LICENSE_ITEMS
        )
        license_label = QLabel(items, self)
        license_label.setTextFormat(Qt.RichText)
        license_label.setStyleSheet("color: #1F2329; line-height: 1.5;")
        self.contentLayout.addWidget(license_label)

        footer = QLabel(
            t("许可证全文位于安装目录 licenses/ 文件夹。"), self
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.contentLayout.addWidget(footer)

        copyright_label = QLabel(t("© 2026 NEX. 保留所有权利。"), self)
        copyright_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.contentLayout.addWidget(copyright_label)

        self.licenses_dir = engines.app_root() / "licenses"
        button_row = QWidget(self)
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.licensesButton = QPushButton(t("打开许可证文件夹"), button_row)
        self.licensesButton.setEnabled(self.licenses_dir.is_dir())
        self.licensesButton.clicked.connect(self._open_licenses)
        button_layout.addWidget(self.licensesButton)
        button_layout.addStretch(1)
        self.contentLayout.addWidget(button_row)

    def _open_licenses(self) -> None:
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.licenses_dir))
        )
