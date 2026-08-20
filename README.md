# Mini Camera Lab

[简体中文](#简体中文) · [English](#english)

## 简体中文

Mini Camera Lab 是一个用于理解、实验和验证 **Physical Toy Camera Engine** 的桌面相机成像实验台。它不是普通的滤镜 Demo，而是把一张 RGB 图片近似转换到线性场景空间，再模拟镜头、传感器和 ISP（Image Signal Processor，图像信号处理）中的主要阶段。

它适合用于：

- 观察从线性场景到最终 sRGB 的完整成像链路；
- 实验 PSF、色差、暗角、Bayer CFA、噪声、ADC 和 ISP 参数；
- 保存和复用 Camera Profile，为后续真实相机测量、标定或 Android Runtime 提供参考；
- 通过 GUI 交互调参，或通过 CLI 对图片进行批处理。

### 成像 Pipeline

```text
Input sRGB
   ↓
Linear Scene（sRGB → 线性场景）
   ↓
Lens / Spatial PSF
   ↓
Chromatic Aberration + Vignette
   ↓
Bayer CFA
   ↓
Shot Noise + Read Noise + Row Noise + FPN
   ↓
ADC / Bit Depth / Black Level
   ↓
Demosaic
   ↓
White Balance
   ↓
3×3 Color Correction Matrix
   ↓
Tone / Saturation
   ↓
Sharpen
   ↓
Final sRGB
```

### 已实现功能

#### Pipeline Stage Preview

GUI 可以查看以下中间结果：

- Input sRGB
- Linear Scene
- After Lens / PSF
- Bayer CFA
- Sensor RAW
- After Demosaic
- After White Balance
- After CCM
- After Tone
- Final sRGB
- Difference vs Input

#### Lens

- 中心 PSF sigma 与边缘 PSF sigma；
- 径向空间混合的 Spatial PSF Approximation；
- Chromatic Aberration；
- Vignetting。

当前 PSF 是为了实时交互而设计的轻量近似，不代表已经测量出的真实镜头 PSF。后续可以把它替换为 measured PSF field 或 PSF basis，而不改变整体数据流。

#### Sensor

- RGGB、BGGR、GRBG、GBRG Bayer CFA；
- 电子空间中的 Poisson Shot Noise；
- Read Noise、Row Noise、Fixed Pattern Noise；
- Full Well Capacity、Analog Gain、Black Level；
- 8–16 bit ADC Quantization；
- 固定 Noise Seed，便于 A/B 对比调参。

#### Demosaic 与 ISP

- OpenCV Bilinear / Edge-aware Demosaic；
- R/G/B White Balance Gain；
- 3×3 Color Correction Matrix（CCM）；
- Exposure EV、Contrast、Black Crush、Highlight Clip；
- Saturation 与 Unsharp Mask Sharpen。

#### Camera Profile

所有 Lens、Sensor 和 ISP 参数都可以保存为 JSON 并重新加载。仓库包含一个可直接使用的示例：`sample_toy_profile.json`。

### 安装与启动

要求：Python 3.10 或更高版本。

#### macOS / Linux

在项目根目录执行：

```bash
./run_macos_linux.sh
```

脚本会创建 `.venv`、安装 `requirements.txt` 中的依赖并启动 GUI。如果脚本没有执行权限，可以先运行：

```bash
chmod +x run_macos_linux.sh
./run_macos_linux.sh
```

也可以手动安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

#### Windows

双击 `run_windows.bat`，或在项目目录的命令提示符中执行：

```bat
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

### GUI 使用教程

1. 点击 **Open Image**，打开 PNG、JPEG、TIFF、BMP 或 WEBP 图片。
2. 左侧显示输入图，右侧显示当前选中的 Pipeline Stage。
3. 使用顶部的 Stage 下拉菜单查看 `Bayer CFA`、`Sensor RAW`、`After Demosaic` 等中间结果。
4. 在右侧的 **Lens**、**Sensor**、**ISP** 标签页中调整参数，预览会自动重新处理。
5. 点击 **Save Profile** 保存当前 Camera Profile；点击 **Load Profile** 可以加载 JSON 配置。
6. 点击 **Save Full-Res**，以原始分辨率重新运行完整 Pipeline 并导出最终结果。

为了保证实时交互，GUI 预览会把最长边缩小到最多 1400 px；完整分辨率导出不会使用缩小后的预览，而是重新处理原图。

### 主要参数速查

| 模块 | 参数 | 含义 |
| --- | --- | --- |
| Lens | `center_sigma` / `edge_sigma` | 中心与边缘的 PSF 模糊程度 |
| Lens | `edge_power` | 从中心到边缘的 PSF 混合曲线 |
| Lens | `ca_pixels` | RGB 通道的径向色差偏移 |
| Lens | `vignette_strength` / `vignette_power` | 暗角强度与径向衰减曲线 |
| Sensor | `bayer_pattern` | Bayer CFA 排列方式 |
| Sensor | `full_well_e` | 满阱电子容量 |
| Sensor | `read_noise_e` / `row_noise_e` | 读出噪声与行噪声，单位为电子 |
| Sensor | `fpn_strength` | 固定模式噪声的增益扰动幅度 |
| Sensor | `analog_gain` | 模拟增益，近似 ISO 链路的一部分 |
| Sensor | `black_level` | RAW 黑电平 |
| Sensor | `bit_depth` | ADC 量化位深，范围为 8–16 |
| Sensor | `seed` | 噪声随机种子，固定后结果可复现 |
| ISP | `wb_r/g/b` | 三个颜色通道的白平衡增益 |
| ISP | `ccm` | 3×3 颜色校正矩阵 |
| ISP | `exposure_ev` / `contrast` | 曝光补偿与对比度 |
| ISP | `black_crush` / `highlight_clip` | 暗部压黑与高光截断 |
| ISP | `saturation` / `sharpen_amount` | 饱和度与反锐化掩模锐化 |

### CLI 批处理

不启动 GUI 时，可以直接对单张图片运行完整 Pipeline：

```bash
python -m camera_lab.cli input.jpg output.png --profile sample_toy_profile.json
```

不指定 profile 时使用 `CameraProfile()` 默认参数：

```bash
python -m camera_lab.cli input.jpg output.jpg
```

参数说明：

- 第一个位置参数：输入图片路径；
- 第二个位置参数：输出图片路径，文件扩展名决定编码格式；
- `--profile`：可选的 Camera Profile JSON。

如果通过 Python 包方式安装，也可以使用 `mini-camera-lab-cli` 命令入口。当前 CLI 会保存 `stages["final"]`，GUI 则额外提供所有中间阶段的可视化。

### 测试

```bash
python -m pytest tests
```

当前测试覆盖：

- RGGB Bayer 到 Demosaic 的基本正确性；
- 完整 Pipeline 的各阶段尺寸与有限值检查；
- 固定 Noise Seed 后结果的可重复性。

### 项目结构

```text
MiniCameraLab/
├── main.py                         # GUI 启动入口
├── requirements.txt                # 运行依赖
├── pyproject.toml                  # 项目元数据与 CLI 入口
├── sample_toy_profile.json         # 示例 Camera Profile
├── run_macos_linux.sh              # macOS / Linux 启动脚本
├── run_windows.bat                 # Windows 启动脚本
├── README.md
├── camera_lab/
│   ├── __init__.py                 # 对外导出 CameraProfile / process_image
│   ├── imaging.py                  # 成像、传感器、Bayer、ISP 基础函数
│   ├── pipeline.py                 # Pipeline 编排与 Stage 输出
│   ├── profile.py                  # Lens / Sensor / ISP 配置模型
│   ├── io_utils.py                 # 图片读写与预览缩放
│   ├── cli.py                      # CLI 批处理入口
│   └── ui/
│       ├── main_window.py          # PySide6 主窗口与交互逻辑
│       ├── image_view.py           # 图片显示控件
│       └── histogram.py             # RGB 直方图控件
└── tests/
    └── test_pipeline.py            # Pipeline 单元测试
```

### 在 Physical Toy Camera 项目中的定位

```text
真实 Toy Camera
       ↓
测量 / 标定
       ↓
Mini Camera Lab
       ↓
验证 Lens / Sensor / ISP Model
       ↓
Camera Profile
       ↓
C++ / GLES / Vulkan Runtime
       ↓
Android Toy Camera App
```

Mini Camera Lab 的职责是 **Reference / Experiment / Calibration**，不是最终的 Android App。当前项目有意没有把以下能力描述成已经完成：

- 真实 DNG / Camera2 RAW Metadata 解码；
- 实测 Spatial PSF Field 导入；
- PSF Basis / PCA 压缩；
- MTF / SFR 自动测量；
- Photon Transfer Curve 自动拟合；
- ColorChecker 自动求 CCM；
- Dark Frame / Flat Field Calibration；
- Reference Camera 与 Simulation 的 ΔE、MTF、Noise Statistical Compare。

这些能力可以作为后续从“实验台”演进为 Camera Characterization Studio 的方向。

## English

Mini Camera Lab is a desktop camera-imaging laboratory for understanding, experimenting with, and validating a **Physical Toy Camera Engine**. It is not a conventional filter demo: an RGB image is approximately converted into a linear scene representation, then passed through simplified lens, sensor, and ISP stages.

Typical uses include:

- Inspecting the complete imaging path from linear scene data to final sRGB;
- Experimenting with PSF, chromatic aberration, vignetting, Bayer CFA, noise, ADC, and ISP parameters;
- Saving and reusing Camera Profiles as references for future camera measurements, calibration, or Android Runtime work;
- Tuning parameters interactively in the GUI or processing images in batch through the CLI.

### Imaging Pipeline

```text
Input sRGB
   ↓
Linear Scene (sRGB → linear scene)
   ↓
Lens / Spatial PSF
   ↓
Chromatic Aberration + Vignette
   ↓
Bayer CFA
   ↓
Shot Noise + Read Noise + Row Noise + FPN
   ↓
ADC / Bit Depth / Black Level
   ↓
Demosaic
   ↓
White Balance
   ↓
3×3 Color Correction Matrix
   ↓
Tone / Saturation
   ↓
Sharpen
   ↓
Final sRGB
```

### Implemented Features

#### Pipeline Stage Preview

The GUI exposes these intermediate results:

- Input sRGB
- Linear Scene
- After Lens / PSF
- Bayer CFA
- Sensor RAW
- After Demosaic
- After White Balance
- After CCM
- After Tone
- Final sRGB
- Difference vs Input

#### Lens

- Center and edge PSF sigma;
- A radially blended spatial PSF approximation;
- Chromatic aberration;
- Vignetting.

The current PSF is a lightweight approximation designed for interactive use. It is not presented as a measured lens PSF. A measured PSF field or PSF basis can be added later without changing the overall data flow.

#### Sensor

- RGGB, BGGR, GRBG, and GBRG Bayer CFA patterns;
- Poisson shot noise in electron space;
- Read noise, row noise, and fixed-pattern noise;
- Full-well capacity, analog gain, and black level;
- 8–16-bit ADC quantization;
- A fixed noise seed for reproducible A/B comparisons.

#### Demosaic and ISP

- OpenCV bilinear and edge-aware demosaicing;
- R/G/B white-balance gains;
- A 3×3 color-correction matrix (CCM);
- Exposure EV, contrast, black crush, and highlight clipping;
- Saturation and unsharp-mask sharpening.

#### Camera Profiles

All lens, sensor, and ISP parameters can be saved to and loaded from JSON. The repository includes a ready-to-use example: `sample_toy_profile.json`.

### Installation and Launch

Requirement: Python 3.10 or newer.

#### macOS / Linux

Run this from the project root:

```bash
./run_macos_linux.sh
```

The script creates `.venv`, installs the dependencies from `requirements.txt`, and launches the GUI. If needed, make it executable first:

```bash
chmod +x run_macos_linux.sh
./run_macos_linux.sh
```

Manual installation is also supported:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

#### Windows

Double-click `run_windows.bat`, or run the following in Command Prompt from the project directory:

```bat
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

### GUI Tutorial

1. Click **Open Image** and choose a PNG, JPEG, TIFF, BMP, or WEBP image.
2. The left pane shows the input image; the right pane shows the selected pipeline stage.
3. Use the stage selector at the top to inspect stages such as `Bayer CFA`, `Sensor RAW`, and `After Demosaic`.
4. Adjust parameters in the **Lens**, **Sensor**, and **ISP** tabs. The preview is reprocessed automatically.
5. Click **Save Profile** to save the current Camera Profile, or **Load Profile** to load a JSON configuration.
6. Click **Save Full-Res** to rerun the complete pipeline at the original image resolution and export the final result.

For responsive interaction, the GUI preview is reduced to a maximum dimension of 1400 px. Full-resolution export reruns the pipeline on the original image rather than on the preview.

### Parameter Quick Reference

| Module | Parameter | Meaning |
| --- | --- | --- |
| Lens | `center_sigma` / `edge_sigma` | Center and edge PSF blur |
| Lens | `edge_power` | Radial blend curve from center to edge |
| Lens | `ca_pixels` | Radial chromatic-aberration offset |
| Lens | `vignette_strength` / `vignette_power` | Vignetting strength and falloff |
| Sensor | `bayer_pattern` | Bayer CFA arrangement |
| Sensor | `full_well_e` | Full-well electron capacity |
| Sensor | `read_noise_e` / `row_noise_e` | Read and row noise in electrons |
| Sensor | `fpn_strength` | Fixed-pattern gain variation |
| Sensor | `analog_gain` | Analog gain, approximating part of the ISO path |
| Sensor | `black_level` | RAW black level |
| Sensor | `bit_depth` | ADC bit depth, from 8 to 16 |
| Sensor | `seed` | Noise seed for reproducible output |
| ISP | `wb_r/g/b` | Per-channel white-balance gains |
| ISP | `ccm` | 3×3 color-correction matrix |
| ISP | `exposure_ev` / `contrast` | Exposure compensation and contrast |
| ISP | `black_crush` / `highlight_clip` | Shadow compression and highlight clipping |
| ISP | `saturation` / `sharpen_amount` | Saturation and unsharp-mask sharpening |

### CLI Batch Processing

Run the complete pipeline without launching the GUI:

```bash
python -m camera_lab.cli input.jpg output.png --profile sample_toy_profile.json
```

Without a profile, the default `CameraProfile()` is used:

```bash
python -m camera_lab.cli input.jpg output.jpg
```

Arguments:

- First positional argument: input image path;
- Second positional argument: output image path; the extension selects the encoding format;
- `--profile`: optional Camera Profile JSON.

When installed as a Python package, the project also exposes the `mini-camera-lab-cli` entry point. The CLI writes `stages["final"]`; the GUI additionally visualizes all intermediate stages.

### Tests

```bash
python -m pytest tests
```

The current tests cover:

- Basic correctness of RGGB Bayer-to-demosaic conversion;
- Shape and finite-value checks for every stage of the full pipeline;
- Deterministic output when the noise seed is fixed.

### Project Structure

```text
MiniCameraLab/
├── main.py                         # GUI entry point
├── requirements.txt                # Runtime dependencies
├── pyproject.toml                  # Project metadata and CLI entry point
├── sample_toy_profile.json         # Example Camera Profile
├── run_macos_linux.sh              # macOS / Linux launcher
├── run_windows.bat                 # Windows launcher
├── README.md
├── camera_lab/
│   ├── __init__.py                 # Public CameraProfile / process_image exports
│   ├── imaging.py                  # Imaging, sensor, Bayer, and ISP primitives
│   ├── pipeline.py                 # Pipeline orchestration and stage outputs
│   ├── profile.py                  # Lens / Sensor / ISP configuration models
│   ├── io_utils.py                 # Image I/O and preview resizing
│   ├── cli.py                      # CLI batch-processing entry point
│   └── ui/
│       ├── main_window.py          # PySide6 window and interaction logic
│       ├── image_view.py           # Image display widget
│       └── histogram.py             # RGB histogram widget
└── tests/
    └── test_pipeline.py            # Pipeline unit tests
```

### Role in the Physical Toy Camera Project

```text
Real Toy Camera
       ↓
Measurement / Calibration
       ↓
Mini Camera Lab
       ↓
Lens / Sensor / ISP Model Validation
       ↓
Camera Profile
       ↓
C++ / GLES / Vulkan Runtime
       ↓
Android Toy Camera App
```

Mini Camera Lab is a **Reference / Experiment / Calibration** tool, not the final Android app. The following capabilities are intentionally not described as complete yet:

- Real DNG / Camera2 RAW metadata decoding;
- Import of measured spatial PSF fields;
- PSF basis / PCA compression;
- Automatic MTF / SFR measurement;
- Automatic photon-transfer-curve fitting;
- Automatic CCM fitting from a ColorChecker;
- Dark-frame / flat-field calibration;
- ΔE, MTF, and noise-statistics comparison between a reference camera and the simulation.

These are possible next steps for evolving the laboratory into a full Camera Characterization Studio.
