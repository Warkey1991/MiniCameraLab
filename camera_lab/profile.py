from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import List


@dataclass
class LensSettings:
    enabled: bool = True
    center_sigma: float = 0.25
    edge_sigma: float = 2.20
    edge_power: float = 2.0
    ca_pixels: float = 1.2
    vignette_strength: float = 0.22
    vignette_power: float = 2.2


@dataclass
class SensorSettings:
    enabled: bool = True
    bayer_pattern: str = "RGGB"
    full_well_e: float = 12000.0
    read_noise_e: float = 5.0
    row_noise_e: float = 1.5
    fpn_strength: float = 0.005
    analog_gain: float = 1.0
    black_level: float = 0.015
    bit_depth: int = 12
    seed: int = 7
    demosaic_method: str = "bilinear"


@dataclass
class ISPSettings:
    enabled: bool = True
    wb_r: float = 1.18
    wb_g: float = 1.00
    wb_b: float = 1.10
    ccm: List[List[float]] = field(default_factory=lambda: [
        [1.08, -0.05, -0.03],
        [-0.04, 1.07, -0.03],
        [-0.02, -0.08, 1.10],
    ])
    exposure_ev: float = 0.0
    contrast: float = 1.08
    black_crush: float = 0.01
    highlight_clip: float = 0.93
    saturation: float = 0.93
    sharpen_amount: float = 0.18
    sharpen_radius: float = 1.0


@dataclass
class CameraProfile:
    name: str = "Mini Camera Lab Default"
    lens: LensSettings = field(default_factory=LensSettings)
    sensor: SensorSettings = field(default_factory=SensorSettings)
    isp: ISPSettings = field(default_factory=ISPSettings)

    def to_dict(self):
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> "CameraProfile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return CameraProfile(
            name=data.get("name", "Loaded Profile"),
            lens=LensSettings(**data.get("lens", {})),
            sensor=SensorSettings(**data.get("sensor", {})),
            isp=ISPSettings(**data.get("isp", {})),
        )
