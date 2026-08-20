from __future__ import annotations

import math
from typing import Dict, Tuple

import cv2
import numpy as np


def srgb_to_linear(img: np.ndarray) -> np.ndarray:
    img = np.clip(img.astype(np.float32), 0.0, 1.0)
    return np.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(img: np.ndarray) -> np.ndarray:
    img = np.clip(img.astype(np.float32), 0.0, 1.0)
    return np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(img, 1.0 / 2.4) - 0.055).astype(np.float32)


def _odd_kernel_size(sigma: float) -> int:
    if sigma <= 0.01:
        return 1
    k = max(3, int(math.ceil(sigma * 6.0)) | 1)
    return min(k, 101)


def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0.01:
        return img.copy()
    k = _odd_kernel_size(sigma)
    return cv2.GaussianBlur(img, (k, k), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REFLECT101)


def spatial_psf_blur(img: np.ndarray, center_sigma: float, edge_sigma: float, edge_power: float = 2.0) -> np.ndarray:
    """Approximate a spatially varying PSF by blending two physically plausible blur fields.

    This is intentionally lightweight for interactive use. It is not a replacement for a measured PSF field,
    but its data flow matches what a later basis-PSF implementation would use.
    """
    h, w = img.shape[:2]
    center = gaussian_blur(img, center_sigma)
    edge = gaussian_blur(img, edge_sigma)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = (w - 1) * 0.5
    cy = (h - 1) * 0.5
    nx = (xx - cx) / max(cx, 1.0)
    ny = (yy - cy) / max(cy, 1.0)
    r = np.sqrt(nx * nx + ny * ny)
    weight = np.clip(r, 0.0, 1.0) ** max(edge_power, 0.1)
    weight = weight[..., None]
    return (center * (1.0 - weight) + edge * weight).astype(np.float32)


def _radial_scale_channel(channel: np.ndarray, scale: float) -> np.ndarray:
    if abs(scale - 1.0) < 1e-6:
        return channel.copy()
    h, w = channel.shape
    cx = (w - 1) * 0.5
    cy = (h - 1) * 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    src_x = (xx - cx) / scale + cx
    src_y = (yy - cy) / scale + cy
    return cv2.remap(channel, src_x, src_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)


def chromatic_aberration(img: np.ndarray, pixels: float) -> np.ndarray:
    if abs(pixels) < 1e-4:
        return img.copy()
    h, w = img.shape[:2]
    ref = max(min(h, w), 1)
    frac = pixels / ref
    out = img.copy()
    out[..., 0] = _radial_scale_channel(img[..., 0], 1.0 + frac)
    out[..., 2] = _radial_scale_channel(img[..., 2], 1.0 - frac)
    return np.clip(out, 0.0, 1.0)


def apply_vignette(img: np.ndarray, strength: float, power: float = 2.0) -> np.ndarray:
    if strength <= 1e-6:
        return img.copy()
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = (w - 1) * 0.5
    cy = (h - 1) * 0.5
    nx = (xx - cx) / max(cx, 1.0)
    ny = (yy - cy) / max(cy, 1.0)
    r = np.clip(np.sqrt(nx * nx + ny * ny) / math.sqrt(2.0), 0.0, 1.0)
    gain = 1.0 - np.clip(strength, 0.0, 1.0) * (r ** max(power, 0.1))
    return np.clip(img * gain[..., None], 0.0, 1.0)


BAYER_CHANNELS: Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]] = {
    "RGGB": ((0, 1), (1, 2)),
    "BGGR": ((2, 1), (1, 0)),
    "GRBG": ((1, 0), (2, 1)),
    "GBRG": ((1, 2), (0, 1)),
}


def rgb_to_bayer(rgb: np.ndarray, pattern: str = "RGGB") -> np.ndarray:
    pattern = pattern.upper()
    if pattern not in BAYER_CHANNELS:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")
    h, w = rgb.shape[:2]
    raw = np.empty((h, w), dtype=np.float32)
    p = BAYER_CHANNELS[pattern]
    raw[0::2, 0::2] = rgb[0::2, 0::2, p[0][0]]
    raw[0::2, 1::2] = rgb[0::2, 1::2, p[0][1]]
    raw[1::2, 0::2] = rgb[1::2, 0::2, p[1][0]]
    raw[1::2, 1::2] = rgb[1::2, 1::2, p[1][1]]
    return raw


def visualize_bayer(raw: np.ndarray, pattern: str = "RGGB") -> np.ndarray:
    h, w = raw.shape
    vis = np.zeros((h, w, 3), dtype=np.float32)
    p = BAYER_CHANNELS[pattern]
    vis[0::2, 0::2, p[0][0]] = raw[0::2, 0::2]
    vis[0::2, 1::2, p[0][1]] = raw[0::2, 1::2]
    vis[1::2, 0::2, p[1][0]] = raw[1::2, 0::2]
    vis[1::2, 1::2, p[1][1]] = raw[1::2, 1::2]
    return np.clip(vis * 1.6, 0.0, 1.0)


_CV_BAYER_RGB = {
    "RGGB": cv2.COLOR_BayerBG2RGB,
    "BGGR": cv2.COLOR_BayerRG2RGB,
    "GRBG": cv2.COLOR_BayerGB2RGB,
    "GBRG": cv2.COLOR_BayerGR2RGB,
}

_CV_BAYER_RGB_EA = {
    "RGGB": cv2.COLOR_BayerBG2RGB_EA,
    "BGGR": cv2.COLOR_BayerRG2RGB_EA,
    "GRBG": cv2.COLOR_BayerGB2RGB_EA,
    "GBRG": cv2.COLOR_BayerGR2RGB_EA,
}


def demosaic(raw: np.ndarray, pattern: str = "RGGB", method: str = "bilinear") -> np.ndarray:
    raw16 = np.clip(raw, 0.0, 1.0)
    raw16 = np.round(raw16 * 65535.0).astype(np.uint16)
    if method == "edge-aware":
        code = _CV_BAYER_RGB_EA[pattern]
    else:
        code = _CV_BAYER_RGB[pattern]
    rgb16 = cv2.cvtColor(raw16, code)
    return (rgb16.astype(np.float32) / 65535.0).clip(0.0, 1.0)


def sensor_simulate(
    signal: np.ndarray,
    full_well_e: float,
    read_noise_e: float,
    row_noise_e: float,
    fpn_strength: float,
    analog_gain: float,
    black_level: float,
    bit_depth: int,
    seed: int,
) -> np.ndarray:
    """Simulate a compact raw sensor model in electron space.

    signal is normalized scene-referred intensity after the CFA.
    - Shot noise uses a Poisson process in electrons.
    - Read and row noise are Gaussian in electrons.
    - FPN is a deterministic multiplicative per-pixel gain map for the selected seed.
    - Analog gain occurs before black level / ADC quantization.
    """
    rng = np.random.default_rng(int(seed))
    signal = np.clip(signal.astype(np.float32), 0.0, 1.0)
    full_well_e = max(float(full_well_e), 1.0)

    fixed_gain = 1.0 + rng.normal(0.0, max(fpn_strength, 0.0), size=signal.shape).astype(np.float32)
    electrons_expected = np.clip(signal * fixed_gain, 0.0, 1.0) * full_well_e
    electrons = rng.poisson(electrons_expected).astype(np.float32)

    if read_noise_e > 0:
        electrons += rng.normal(0.0, read_noise_e, size=signal.shape).astype(np.float32)
    if row_noise_e > 0:
        row = rng.normal(0.0, row_noise_e, size=(signal.shape[0], 1)).astype(np.float32)
        electrons += row

    normalized = electrons / full_well_e
    normalized *= max(float(analog_gain), 0.01)
    normalized += float(black_level)

    levels = float((1 << int(np.clip(bit_depth, 8, 16))) - 1)
    normalized = np.clip(normalized, 0.0, 1.0)
    normalized = np.round(normalized * levels) / levels
    return normalized.astype(np.float32)


def remove_black_level(raw: np.ndarray, black_level: float) -> np.ndarray:
    denom = max(1.0 - black_level, 1e-6)
    return np.clip((raw - black_level) / denom, 0.0, 1.0).astype(np.float32)


def white_balance(rgb: np.ndarray, gains: Tuple[float, float, float]) -> np.ndarray:
    g = np.asarray(gains, dtype=np.float32).reshape(1, 1, 3)
    return np.clip(rgb * g, 0.0, 4.0).astype(np.float32)


def apply_ccm(rgb: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    m = np.asarray(matrix, dtype=np.float32).reshape(3, 3)
    out = np.tensordot(rgb, m.T, axes=1)
    return np.clip(out, 0.0, 4.0).astype(np.float32)


def apply_tone(rgb: np.ndarray, exposure_ev: float, contrast: float, black_crush: float, highlight_clip: float) -> np.ndarray:
    x = np.clip(rgb * (2.0 ** exposure_ev), 0.0, 8.0)
    # Soft black crush: increase the threshold at which shadows are pulled toward zero.
    b = np.clip(black_crush, 0.0, 0.5)
    if b > 0:
        x = np.clip((x - b) / max(1.0 - b, 1e-6), 0.0, None)

    # Contrast in linear space around a middle-gray pivot.
    c = max(float(contrast), 0.05)
    pivot = 0.18
    x = np.clip((x - pivot) * c + pivot, 0.0, None)

    hc = float(np.clip(highlight_clip, 0.1, 1.0))
    x = np.minimum(x, hc) / hc
    return np.clip(x, 0.0, 1.0).astype(np.float32)


def apply_saturation(rgb: np.ndarray, saturation: float) -> np.ndarray:
    sat = max(float(saturation), 0.0)
    luma = (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722)[..., None]
    return np.clip(luma + (rgb - luma) * sat, 0.0, 1.0).astype(np.float32)


def unsharp_mask(img: np.ndarray, amount: float, radius: float = 1.0) -> np.ndarray:
    if amount <= 1e-5:
        return img.copy()
    blurred = gaussian_blur(img, max(radius, 0.1))
    return np.clip(img + float(amount) * (img - blurred), 0.0, 1.0).astype(np.float32)
