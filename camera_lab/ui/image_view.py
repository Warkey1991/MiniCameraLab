from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class ImageView(QLabel):
    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self._pixmap_original = None
        self.setText(placeholder)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("QLabel { background:#15171a; color:#9aa0a6; border:1px solid #2b2f33; }")

    def set_rgb(self, rgb: np.ndarray | None):
        if rgb is None:
            self._pixmap_original = None
            self.clear()
            return
        arr = np.clip(rgb, 0.0, 1.0)
        arr8 = np.ascontiguousarray(np.round(arr * 255.0).astype(np.uint8))
        h, w = arr8.shape[:2]
        image = QImage(arr8.data, w, h, arr8.strides[0], QImage.Format_RGB888).copy()
        self._pixmap_original = QPixmap.fromImage(image)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        if self._pixmap_original is None:
            return
        self.setPixmap(self._pixmap_original.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
