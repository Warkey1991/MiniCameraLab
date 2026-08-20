from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..io_utils import load_image_rgb, resize_preview, save_image_rgb
from ..pipeline import STAGE_LABELS, process_image
from ..profile import CameraProfile
from .histogram import HistogramWidget
from .image_view import ImageView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Camera Lab — Physical Camera Pipeline")
        self.resize(1500, 900)

        self.profile = CameraProfile()
        self.full_image = None
        self.preview_image = None
        self.stages = None
        self.current_path = None
        self._loading_ui = False

        self.process_timer = QTimer(self)
        self.process_timer.setSingleShot(True)
        self.process_timer.setInterval(80)
        self.process_timer.timeout.connect(self.process_preview)

        self._build_menu()
        self._build_ui()
        self._load_profile_to_ui()
        self.statusBar().showMessage("Open an image to begin. JPEG/PNG/TIFF are supported by the OpenCV build.")

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")
        actions = [
            ("Open Image…", self.open_image),
            ("Save Full-Resolution Output…", self.save_output),
            ("Load Camera Profile…", self.load_profile),
            ("Save Camera Profile…", self.save_profile),
            ("Reset Profile", self.reset_profile),
        ]
        for text, fn in actions:
            a = QAction(text, self)
            a.triggered.connect(fn)
            menu.addAction(a)

    def _build_ui(self):
        root = QSplitter(Qt.Horizontal)
        self.setCentralWidget(root)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        header = QHBoxLayout()
        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self.open_image)
        save_btn = QPushButton("Save Full-Res")
        save_btn.clicked.connect(self.save_output)
        header.addWidget(open_btn)
        header.addWidget(save_btn)
        header.addSpacing(18)
        header.addWidget(QLabel("Preview stage:"))
        self.stage_combo = QComboBox()
        for key, label in STAGE_LABELS.items():
            self.stage_combo.addItem(label, key)
        self.stage_combo.setCurrentIndex(list(STAGE_LABELS.keys()).index("final"))
        self.stage_combo.currentIndexChanged.connect(self.update_views)
        header.addWidget(self.stage_combo, 1)
        left_layout.addLayout(header)

        image_split = QSplitter(Qt.Horizontal)
        self.original_view = ImageView("Input image")
        self.stage_view = ImageView("Processed stage")
        image_split.addWidget(self.original_view)
        image_split.addWidget(self.stage_view)
        image_split.setSizes([700, 700])
        left_layout.addWidget(image_split, 1)

        self.histogram = HistogramWidget()
        left_layout.addWidget(self.histogram)
        self.info_label = QLabel("No image loaded")
        left_layout.addWidget(self.info_label)

        root.addWidget(left)
        root.addWidget(self._build_controls())
        root.setSizes([1120, 380])

    def _build_controls(self):
        tabs = QTabWidget()
        tabs.addTab(self._lens_tab(), "Lens")
        tabs.addTab(self._sensor_tab(), "Sensor")
        tabs.addTab(self._isp_tab(), "ISP")
        tabs.setMinimumWidth(360)
        return tabs

    def _make_double(self, lo, hi, step, decimals=3):
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setSingleStep(step)
        w.setDecimals(decimals)
        w.valueChanged.connect(self._ui_changed)
        return w

    def _make_int(self, lo, hi, step=1):
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setSingleStep(step)
        w.valueChanged.connect(self._ui_changed)
        return w

    def _wrap_scroll(self, body):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        return scroll

    def _lens_tab(self):
        body = QWidget()
        form = QFormLayout(body)
        self.lens_enabled = QCheckBox("Enable physical lens stage")
        self.lens_enabled.toggled.connect(self._ui_changed)
        form.addRow(self.lens_enabled)
        self.center_sigma = self._make_double(0.0, 8.0, 0.05, 2)
        self.edge_sigma = self._make_double(0.0, 16.0, 0.10, 2)
        self.edge_power = self._make_double(0.2, 6.0, 0.1, 2)
        self.ca_pixels = self._make_double(-12.0, 12.0, 0.1, 2)
        self.vignette = self._make_double(0.0, 1.0, 0.01, 2)
        self.vignette_power = self._make_double(0.2, 6.0, 0.1, 2)
        form.addRow("Center PSF σ", self.center_sigma)
        form.addRow("Edge PSF σ", self.edge_sigma)
        form.addRow("Edge falloff power", self.edge_power)
        form.addRow("Chromatic aberration (px)", self.ca_pixels)
        form.addRow("Vignette strength", self.vignette)
        form.addRow("Vignette power", self.vignette_power)
        tip = QLabel("PSF is modeled as a lightweight spatially varying blur field: center and edge kernels are blended radially. This keeps the same conceptual structure as a later measured PSF-basis renderer.")
        tip.setWordWrap(True)
        form.addRow(tip)
        return self._wrap_scroll(body)

    def _sensor_tab(self):
        body = QWidget()
        form = QFormLayout(body)
        self.sensor_enabled = QCheckBox("Enable Bayer + sensor simulation")
        self.sensor_enabled.toggled.connect(self._ui_changed)
        form.addRow(self.sensor_enabled)
        self.bayer_pattern = QComboBox()
        self.bayer_pattern.addItems(["RGGB", "BGGR", "GRBG", "GBRG"])
        self.bayer_pattern.currentTextChanged.connect(self._ui_changed)
        self.demosaic = QComboBox()
        self.demosaic.addItems(["bilinear", "edge-aware"])
        self.demosaic.currentTextChanged.connect(self._ui_changed)
        self.full_well = self._make_double(500.0, 100000.0, 500.0, 0)
        self.read_noise = self._make_double(0.0, 100.0, 0.5, 2)
        self.row_noise = self._make_double(0.0, 100.0, 0.25, 2)
        self.fpn = self._make_double(0.0, 0.10, 0.001, 4)
        self.analog_gain = self._make_double(0.10, 16.0, 0.1, 2)
        self.black_level = self._make_double(0.0, 0.25, 0.001, 4)
        self.bit_depth = self._make_int(8, 16)
        self.seed = self._make_int(0, 999999)
        form.addRow("Bayer CFA", self.bayer_pattern)
        form.addRow("Demosaic", self.demosaic)
        form.addRow("Full well (electrons)", self.full_well)
        form.addRow("Read noise (e-)", self.read_noise)
        form.addRow("Row noise (e-)", self.row_noise)
        form.addRow("FPN σ (fraction)", self.fpn)
        form.addRow("Analog gain", self.analog_gain)
        form.addRow("Black level", self.black_level)
        form.addRow("ADC bit depth", self.bit_depth)
        form.addRow("Noise seed", self.seed)
        tip = QLabel("Shot noise is generated by a Poisson process in electron space. Read/row noise are Gaussian. The seed is fixed so parameter changes are visually comparable.")
        tip.setWordWrap(True)
        form.addRow(tip)
        return self._wrap_scroll(body)

    def _isp_tab(self):
        body = QWidget()
        layout = QVBoxLayout(body)
        form = QFormLayout()
        self.isp_enabled = QCheckBox("Enable ISP")
        self.isp_enabled.toggled.connect(self._ui_changed)
        form.addRow(self.isp_enabled)
        self.wb_r = self._make_double(0.25, 4.0, 0.02, 3)
        self.wb_g = self._make_double(0.25, 4.0, 0.02, 3)
        self.wb_b = self._make_double(0.25, 4.0, 0.02, 3)
        self.exposure = self._make_double(-4.0, 4.0, 0.1, 2)
        self.contrast = self._make_double(0.20, 3.0, 0.02, 2)
        self.black_crush = self._make_double(0.0, 0.4, 0.005, 3)
        self.highlight_clip = self._make_double(0.20, 1.0, 0.01, 3)
        self.saturation = self._make_double(0.0, 2.5, 0.02, 2)
        self.sharpen = self._make_double(0.0, 2.0, 0.02, 2)
        self.sharpen_radius = self._make_double(0.1, 5.0, 0.1, 2)
        form.addRow("WB Red gain", self.wb_r)
        form.addRow("WB Green gain", self.wb_g)
        form.addRow("WB Blue gain", self.wb_b)
        form.addRow("Exposure (EV)", self.exposure)
        form.addRow("Contrast", self.contrast)
        form.addRow("Black crush", self.black_crush)
        form.addRow("Highlight clip", self.highlight_clip)
        form.addRow("Saturation", self.saturation)
        form.addRow("Sharpen amount", self.sharpen)
        form.addRow("Sharpen radius", self.sharpen_radius)
        layout.addLayout(form)

        ccm_box = QGroupBox("3×3 Color Correction Matrix")
        grid = QGridLayout(ccm_box)
        self.ccm_cells = []
        for r in range(3):
            row = []
            for c in range(3):
                s = self._make_double(-3.0, 3.0, 0.01, 4)
                grid.addWidget(s, r, c)
                row.append(s)
            self.ccm_cells.append(row)
        layout.addWidget(ccm_box)

        profile_row = QHBoxLayout()
        load_btn = QPushButton("Load Profile")
        save_btn = QPushButton("Save Profile")
        reset_btn = QPushButton("Reset")
        load_btn.clicked.connect(self.load_profile)
        save_btn.clicked.connect(self.save_profile)
        reset_btn.clicked.connect(self.reset_profile)
        profile_row.addWidget(load_btn)
        profile_row.addWidget(save_btn)
        profile_row.addWidget(reset_btn)
        layout.addLayout(profile_row)
        layout.addStretch(1)
        return self._wrap_scroll(body)

    def _ui_changed(self, *args):
        if self._loading_ui:
            return
        self._read_ui_to_profile()
        if self.preview_image is not None:
            self.process_timer.start()

    def _read_ui_to_profile(self):
        p = self.profile
        p.lens.enabled = self.lens_enabled.isChecked()
        p.lens.center_sigma = self.center_sigma.value()
        p.lens.edge_sigma = self.edge_sigma.value()
        p.lens.edge_power = self.edge_power.value()
        p.lens.ca_pixels = self.ca_pixels.value()
        p.lens.vignette_strength = self.vignette.value()
        p.lens.vignette_power = self.vignette_power.value()

        p.sensor.enabled = self.sensor_enabled.isChecked()
        p.sensor.bayer_pattern = self.bayer_pattern.currentText()
        p.sensor.demosaic_method = self.demosaic.currentText()
        p.sensor.full_well_e = self.full_well.value()
        p.sensor.read_noise_e = self.read_noise.value()
        p.sensor.row_noise_e = self.row_noise.value()
        p.sensor.fpn_strength = self.fpn.value()
        p.sensor.analog_gain = self.analog_gain.value()
        p.sensor.black_level = self.black_level.value()
        p.sensor.bit_depth = self.bit_depth.value()
        p.sensor.seed = self.seed.value()

        p.isp.enabled = self.isp_enabled.isChecked()
        p.isp.wb_r = self.wb_r.value()
        p.isp.wb_g = self.wb_g.value()
        p.isp.wb_b = self.wb_b.value()
        p.isp.exposure_ev = self.exposure.value()
        p.isp.contrast = self.contrast.value()
        p.isp.black_crush = self.black_crush.value()
        p.isp.highlight_clip = self.highlight_clip.value()
        p.isp.saturation = self.saturation.value()
        p.isp.sharpen_amount = self.sharpen.value()
        p.isp.sharpen_radius = self.sharpen_radius.value()
        p.isp.ccm = [[self.ccm_cells[r][c].value() for c in range(3)] for r in range(3)]

    def _load_profile_to_ui(self):
        p = self.profile
        self._loading_ui = True
        try:
            self.lens_enabled.setChecked(p.lens.enabled)
            self.center_sigma.setValue(p.lens.center_sigma)
            self.edge_sigma.setValue(p.lens.edge_sigma)
            self.edge_power.setValue(p.lens.edge_power)
            self.ca_pixels.setValue(p.lens.ca_pixels)
            self.vignette.setValue(p.lens.vignette_strength)
            self.vignette_power.setValue(p.lens.vignette_power)

            self.sensor_enabled.setChecked(p.sensor.enabled)
            self.bayer_pattern.setCurrentText(p.sensor.bayer_pattern)
            self.demosaic.setCurrentText(p.sensor.demosaic_method)
            self.full_well.setValue(p.sensor.full_well_e)
            self.read_noise.setValue(p.sensor.read_noise_e)
            self.row_noise.setValue(p.sensor.row_noise_e)
            self.fpn.setValue(p.sensor.fpn_strength)
            self.analog_gain.setValue(p.sensor.analog_gain)
            self.black_level.setValue(p.sensor.black_level)
            self.bit_depth.setValue(p.sensor.bit_depth)
            self.seed.setValue(p.sensor.seed)

            self.isp_enabled.setChecked(p.isp.enabled)
            self.wb_r.setValue(p.isp.wb_r)
            self.wb_g.setValue(p.isp.wb_g)
            self.wb_b.setValue(p.isp.wb_b)
            self.exposure.setValue(p.isp.exposure_ev)
            self.contrast.setValue(p.isp.contrast)
            self.black_crush.setValue(p.isp.black_crush)
            self.highlight_clip.setValue(p.isp.highlight_clip)
            self.saturation.setValue(p.isp.saturation)
            self.sharpen.setValue(p.isp.sharpen_amount)
            self.sharpen_radius.setValue(p.isp.sharpen_radius)
            for r in range(3):
                for c in range(3):
                    self.ccm_cells[r][c].setValue(p.isp.ccm[r][c])
        finally:
            self._loading_ui = False

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp);;All files (*)")
        if not path:
            return
        try:
            img = load_image_rgb(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        self.current_path = path
        self.full_image = img
        self.preview_image = resize_preview(img, 1400)
        self.original_view.set_rgb(self.preview_image)
        self.info_label.setText(f"{Path(path).name} — full {img.shape[1]}×{img.shape[0]}, preview {self.preview_image.shape[1]}×{self.preview_image.shape[0]}")
        self.process_preview()

    def process_preview(self):
        if self.preview_image is None:
            return
        self._read_ui_to_profile()
        try:
            self.stages = process_image(self.preview_image, copy.deepcopy(self.profile))
        except Exception as exc:
            QMessageBox.critical(self, "Processing error", str(exc))
            return
        self.update_views()
        self.statusBar().showMessage(f"Preview processed — profile: {self.profile.name}")

    def update_views(self):
        if not self.stages:
            return
        key = self.stage_combo.currentData()
        image = self.stages.get(key, self.stages["final"])
        self.stage_view.set_rgb(image)
        self.histogram.set_image(image)

    def save_output(self):
        if self.full_image is None:
            QMessageBox.information(self, "Nothing to save", "Open an image first.")
            return
        default = "output.png"
        if self.current_path:
            default = str(Path(self.current_path).with_name(Path(self.current_path).stem + "_mini_camera_lab.png"))
        path, _ = QFileDialog.getSaveFileName(self, "Save Full-Resolution Output", default, "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tif *.tiff)")
        if not path:
            return
        try:
            self.statusBar().showMessage("Processing full resolution…")
            stages = process_image(self.full_image, copy.deepcopy(self.profile))
            save_image_rgb(path, stages["final"])
            self.statusBar().showMessage(f"Saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def load_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Camera Profile", "", "Camera Profile (*.json)")
        if not path:
            return
        try:
            self.profile = CameraProfile.load(path)
            self._load_profile_to_ui()
            if self.preview_image is not None:
                self.process_preview()
            self.statusBar().showMessage(f"Loaded profile: {self.profile.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Load profile failed", str(exc))

    def save_profile(self):
        self._read_ui_to_profile()
        path, _ = QFileDialog.getSaveFileName(self, "Save Camera Profile", "camera_profile.json", "Camera Profile (*.json)")
        if not path:
            return
        try:
            self.profile.save(path)
            self.statusBar().showMessage(f"Saved profile: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save profile failed", str(exc))

    def reset_profile(self):
        self.profile = CameraProfile()
        self._load_profile_to_ui()
        if self.preview_image is not None:
            self.process_preview()
