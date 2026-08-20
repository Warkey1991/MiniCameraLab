from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


def load_image_rgb(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Unable to decode image: {path}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if img.dtype == np.uint8:
        out = img.astype(np.float32) / 255.0
    elif img.dtype == np.uint16:
        out = img.astype(np.float32) / 65535.0
    else:
        out = img.astype(np.float32)
        maxv = float(np.max(out)) if out.size else 1.0
        if maxv > 1.0:
            out /= maxv
    return np.clip(out, 0.0, 1.0)


def save_image_rgb(path: str, rgb: np.ndarray) -> None:
    rgb = np.clip(rgb, 0.0, 1.0)
    ext = Path(path).suffix.lower()
    if ext in {".tif", ".tiff", ".png"}:
        arr = np.round(rgb * 65535.0).astype(np.uint16)
    else:
        arr = np.round(rgb * 255.0).astype(np.uint8)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok, encoded = cv2.imencode(ext if ext else ".png", bgr)
    if not ok:
        raise ValueError(f"Unable to encode output: {path}")
    encoded.tofile(path)


def resize_preview(rgb: np.ndarray, max_dim: int = 1400) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = min(1.0, float(max_dim) / max(h, w))
    if scale >= 1.0:
        return rgb.copy()
    return cv2.resize(rgb, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)
