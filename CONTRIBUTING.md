# Contributing to Mini Camera Lab

[简体中文](#简体中文) · [English](#english)

## 简体中文

欢迎为 Mini Camera Lab 提交 Issue、改进代码、补充测试、完善文档或提出新的成像模型。

### 建议流程

1. Fork 本项目并创建独立分支。
2. 在修改前先通过 Issue 描述 Bug、功能需求或技术方案。
3. 保持改动聚焦，并补充或更新相关测试与文档。
4. 提交前运行：

   ```bash
   python -m pytest tests
   ```

5. 提交 Pull Request，并说明改动内容、验证方式和可能的兼容性影响。

### 贡献约定

- 不要提交 `.venv`、缓存、编译产物或临时生成的图片；README 使用的截图或示例素材请放在 `docs/images/`。
- 新增成像参数时，请在 `CameraProfile`、GUI 控件、README 参数表和测试中保持同步。
- 尽量保持现有的物理含义、数据流和可复现 Noise Seed 设计。
- 提交代码前请确认没有包含密钥、个人路径或其他敏感信息。

所有贡献都将按照本项目的 [MIT License](LICENSE) 发布。

## English

Contributions to Mini Camera Lab are welcome, including bug fixes, tests, documentation improvements, and new imaging models.

### Suggested workflow

1. Fork the project and create a dedicated branch.
2. Before large changes, describe the bug, feature request, or technical design in an Issue.
3. Keep the change focused and update the relevant tests and documentation.
4. Run the test suite before submitting:

   ```bash
   python -m pytest tests
   ```

5. Open a Pull Request describing the change, validation steps, and any compatibility impact.

### Contribution guidelines

- Do not commit `.venv`, caches, build artifacts, or temporary images; README screenshots and example assets belong in `docs/images/`.
- When adding an imaging parameter, keep `CameraProfile`, the GUI controls, the README parameter table, and tests in sync.
- Preserve the existing physical meaning, data flow, and reproducible noise-seed design whenever possible.
- Check that commits do not contain credentials, personal paths, or other sensitive information.

All contributions are released under this project's [MIT License](LICENSE).
