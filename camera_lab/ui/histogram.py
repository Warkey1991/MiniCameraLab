from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self._hist = None

    def set_image(self, rgb):
        if rgb is None:
            self._hist = None
        else:
            hists = []
            for c in range(3):
                vals = np.clip(rgb[..., c], 0.0, 1.0)
                hist, _ = np.histogram(vals, bins=128, range=(0.0, 1.0))
                hists.append(hist.astype(np.float32))
            hist = np.stack(hists)
            hist /= max(float(hist.max()), 1.0)
            self._hist = hist
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        if self._hist is None:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignCenter, "Histogram")
            return
        colors = [Qt.red, Qt.green, Qt.blue]
        w = max(self.width() - 8, 1)
        h = max(self.height() - 8, 1)
        for c in range(3):
            painter.setPen(QPen(colors[c], 1))
            hist = self._hist[c]
            last_x = 4
            last_y = 4 + h
            for i, v in enumerate(hist):
                x = 4 + int(i / (len(hist) - 1) * w)
                y = 4 + h - int(v * h)
                painter.drawLine(last_x, last_y, x, y)
                last_x, last_y = x, y
