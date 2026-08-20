from __future__ import annotations

from collections import OrderedDict
from typing import Dict

import numpy as np

from .imaging import (
    apply_ccm,
    apply_saturation,
    apply_tone,
    apply_vignette,
    chromatic_aberration,
    demosaic,
    linear_to_srgb,
    remove_black_level,
    rgb_to_bayer,
    sensor_simulate,
    spatial_psf_blur,
    srgb_to_linear,
    unsharp_mask,
    visualize_bayer,
    white_balance,
)
from .profile import CameraProfile


STAGE_LABELS = OrderedDict([
    ("input_srgb", "Input sRGB"),
    ("linear_scene", "Linear Scene"),
    ("after_lens", "After Lens / PSF"),
    ("bayer", "Bayer CFA"),
    ("sensor_raw", "Sensor RAW"),
    ("demosaic", "After Demosaic"),
    ("white_balance", "After White Balance"),
    ("ccm", "After CCM"),
    ("tone", "After Tone"),
    ("final", "Final sRGB"),
    ("difference", "Difference vs Input"),
])


def process_image(input_srgb: np.ndarray, profile: CameraProfile) -> Dict[str, np.ndarray]:
    p = profile
    src = np.clip(input_srgb.astype(np.float32), 0.0, 1.0)
    stages: Dict[str, np.ndarray] = {"input_srgb": src}

    linear = srgb_to_linear(src)
    stages["linear_scene"] = linear

    lens = linear
    if p.lens.enabled:
        lens = spatial_psf_blur(lens, p.lens.center_sigma, p.lens.edge_sigma, p.lens.edge_power)
        lens = chromatic_aberration(lens, p.lens.ca_pixels)
        lens = apply_vignette(lens, p.lens.vignette_strength, p.lens.vignette_power)
    stages["after_lens"] = np.clip(lens, 0.0, 1.0)

    if p.sensor.enabled:
        raw = rgb_to_bayer(lens, p.sensor.bayer_pattern)
        stages["bayer"] = visualize_bayer(raw, p.sensor.bayer_pattern)

        noisy_raw = sensor_simulate(
            raw,
            p.sensor.full_well_e,
            p.sensor.read_noise_e,
            p.sensor.row_noise_e,
            p.sensor.fpn_strength,
            p.sensor.analog_gain,
            p.sensor.black_level,
            p.sensor.bit_depth,
            p.sensor.seed,
        )
        # Sensor raw visualization is monochrome on purpose.
        stages["sensor_raw"] = np.repeat(noisy_raw[..., None], 3, axis=2)
        raw_black_removed = remove_black_level(noisy_raw, p.sensor.black_level)
        dem = demosaic(raw_black_removed, p.sensor.bayer_pattern, p.sensor.demosaic_method)
    else:
        stages["bayer"] = lens
        stages["sensor_raw"] = lens
        dem = lens

    stages["demosaic"] = np.clip(dem, 0.0, 1.0)

    if p.isp.enabled:
        wb = white_balance(dem, (p.isp.wb_r, p.isp.wb_g, p.isp.wb_b))
        stages["white_balance"] = np.clip(wb, 0.0, 1.0)

        ccm = apply_ccm(wb, np.array(p.isp.ccm, dtype=np.float32))
        stages["ccm"] = np.clip(ccm, 0.0, 1.0)

        tone = apply_tone(ccm, p.isp.exposure_ev, p.isp.contrast, p.isp.black_crush, p.isp.highlight_clip)
        tone = apply_saturation(tone, p.isp.saturation)
        stages["tone"] = tone

        final = linear_to_srgb(tone)
        final = unsharp_mask(final, p.isp.sharpen_amount, p.isp.sharpen_radius)
    else:
        wb = dem
        ccm = dem
        tone = dem
        stages["white_balance"] = wb
        stages["ccm"] = ccm
        stages["tone"] = tone
        final = linear_to_srgb(np.clip(dem, 0.0, 1.0))

    stages["final"] = np.clip(final, 0.0, 1.0)
    stages["difference"] = np.clip(np.abs(stages["final"] - src) * 3.0, 0.0, 1.0)
    return stages
