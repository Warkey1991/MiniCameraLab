import numpy as np

from camera_lab.imaging import rgb_to_bayer, demosaic
from camera_lab.pipeline import process_image
from camera_lab.profile import CameraProfile


def test_bayer_and_demosaic_constant_color():
    rgb = np.zeros((16, 16, 3), np.float32)
    rgb[..., 0] = 0.8
    rgb[..., 1] = 0.4
    rgb[..., 2] = 0.2
    raw = rgb_to_bayer(rgb, "RGGB")
    out = demosaic(raw, "RGGB", "bilinear")
    center = out[4:-4, 4:-4].mean(axis=(0, 1))
    assert np.allclose(center, [0.8, 0.4, 0.2], atol=0.02)


def test_pipeline_all_stages_shape():
    rng = np.random.default_rng(0)
    image = rng.random((64, 96, 3), dtype=np.float32)
    stages = process_image(image, CameraProfile())
    for key, value in stages.items():
        assert value.shape == image.shape, key
        assert np.isfinite(value).all(), key


def test_noise_seed_is_deterministic():
    image = np.full((48, 64, 3), 0.3, np.float32)
    p = CameraProfile()
    a = process_image(image, p)["sensor_raw"]
    b = process_image(image, p)["sensor_raw"]
    assert np.array_equal(a, b)
