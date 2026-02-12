# HEIC 转 JPG 转换器

[![测试](https://github.com/cnkang/heic2jpg/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/test.yml)
[![代码检查](https://github.com/cnkang/heic2jpg/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/lint.yml)
[![安全扫描](https://github.com/cnkang/heic2jpg/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/cnkang/heic2jpg/actions/workflows/security.yml)
[![Snyk 安全](https://snyk.io/test/github/cnkang/heic2jpg/badge.svg)](https://app.snyk.io/org/cnkang/project/2f2047b4-1dda-4279-829d-288e99acd28a)
[![覆盖率](https://codecov.io/gh/cnkang/heic2jpg/graph/badge.svg?branch=main)](https://codecov.io/gh/cnkang/heic2jpg)
[![Python 版本](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcnkang%2Fheic2jpg%2Fmain%2Fpyproject.toml&query=%24.project.requires-python&label=python&logo=python)](https://github.com/cnkang/heic2jpg/blob/main/pyproject.toml)
[![许可证: MIT](https://img.shields.io/github/license/cnkang/heic2jpg)](LICENSE)

一个将 iPhone HEIC 照片转换为高质量 JPG 格式的 Python 应用程序，专为银盐（模拟）打印优化。

## 项目状态

- 🚧 **Alpha 阶段 / 持续开发中**
- ✅ **CI 检查**：通过 GitHub Actions 自动执行测试、代码检查与安全扫描
- 📊 **覆盖率**：通过 Codecov 自动跟踪
- 📦 **项目标识**：`heic2jpg`

## 命名与目录约定

- `heic2jpg` 是仓库名、项目标识和主 CLI 命令名。
- `src/heic2jpg` 作为 Python 包命名空间被有意保留，用于避免破坏既有导入路径、测试与工具链集成。
- `.kiro/specs/heic2jpg` 已与当前项目标识保持一致。

## 为什么这不是“再造轮子”

- 项目复用成熟基础库（`pillow`、`pillow-heif`、`opencv-python`），并不重复实现编解码器或通用滤镜能力。
- 主要价值是通用转换器不具备的“银盐打印导向”优化逻辑：逐图分析、自适应参数、对逆光/高光/弱光场景的保守且可控处理。
- 保留打印相关关键信息与可追溯数据（EXIF、ICC 色彩配置、metrics JSON），便于质量复核与持续调优。
- 同时具备工程化护栏：安全的路径/文件校验、批处理错误隔离、自动化 CI 与安全扫描。

## 功能特性

- **高质量**：默认质量 100（JPEG 最低压缩），确保最佳打印质量
- **逐图优化**：每张照片单独分析和优化
- **并行处理**：使用多个 CPU 核心快速批量转换
- **元数据与色彩配置保留**：保留 EXIF 元数据与嵌入式 ICC 色彩配置
- **跨平台**：支持 macOS、Windows 和 Linux
- **智能调整**：处理具有挑战性的光照条件（过曝、逆光、弱光）
- **逆光人像恢复**：优先使用嵌入式 XMP 人脸区域（若存在），并在强背光下对人脸进行局部提亮且保护高光背景细节

## 系统要求

- Python 3.14 或更高版本
- uv 包管理器

## 安装

### 前置要求

1. **Python 3.14+**：确保已安装 Python 3.14 或更高版本
   ```bash
   python --version  # 应该显示 3.14.x 或更高
   ```

2. **uv 包管理器**：如果还没有安装 uv
   ```bash
   pip install uv
   ```

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/cnkang/heic2jpg.git
cd heic2jpg

# 2. 安装依赖
uv sync

# 3. 安装命令行工具（以开发模式）
uv pip install -e .

# 4. 验证安装
heic2jpg --version
```

安装完成后，`heic2jpg` 命令就可以在任何目录使用了。

### 快速测试

```bash
# 测试转换（假设你有一个 test.heic 文件）
heic2jpg test.heic

# 如果没有 HEIC 文件，可以先运行测试确保一切正常
uv run pytest tests/unit -v
```

## 使用方法

### 单文件转换

```bash
# 转换单个文件（输出到同一目录）
heic2jpg photo.heic

# 使用自定义质量转换
heic2jpg photo.heic --quality 95

# 转换到指定目录
heic2jpg photo.heic --output-dir ./converted
```

### 批量转换同一目录下的所有 HEIC 文件

```bash
# 方法 1: 使用通配符（推荐）
heic2jpg *.heic

# 方法 2: 使用通配符并指定输出目录
heic2jpg *.heic --output-dir ./converted

# 方法 3: 明确指定多个文件
heic2jpg photo1.heic photo2.heic photo3.heic

# 方法 4: 批量转换且不覆盖已存在的文件
heic2jpg *.heic --no-overwrite

# 方法 5: 批量转换并显示详细日志
heic2jpg *.heic --verbose
```

### 高级用法

```bash
# 批量转换，自定义质量，输出到指定目录
heic2jpg *.heic --quality 95 --output-dir ./converted

# 批量转换，不覆盖现有文件，显示详细日志
heic2jpg *.heic --no-overwrite --verbose

# 显示帮助信息
heic2jpg --help

# 显示版本信息
heic2jpg --version
```

### 使用示例

假设你有一个包含多张 iPhone 照片的目录：

```bash
# 当前目录结构
photos/
  ├── IMG_0001.heic
  ├── IMG_0002.heic
  ├── IMG_0003.heic
  └── IMG_0004.heic

# 进入照片目录
cd photos

# 批量转换所有 HEIC 文件到当前目录
heic2jpg *.heic

# 转换后的目录结构
photos/
  ├── IMG_0001.heic
  ├── IMG_0001.jpg    ← 新生成
  ├── IMG_0002.heic
  ├── IMG_0002.jpg    ← 新生成
  ├── IMG_0003.heic
  ├── IMG_0003.jpg    ← 新生成
  ├── IMG_0004.heic
  └── IMG_0004.jpg    ← 新生成
```

或者输出到单独的目录：

```bash
# 批量转换并输出到 converted 目录
heic2jpg *.heic --output-dir ./converted

# 转换后的目录结构
photos/
  ├── IMG_0001.heic
  ├── IMG_0002.heic
  ├── IMG_0003.heic
  ├── IMG_0004.heic
  └── converted/
      ├── IMG_0001.jpg
      ├── IMG_0002.jpg
      ├── IMG_0003.jpg
      └── IMG_0004.jpg
```

## 开发

### 设置开发环境

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 运行代码检查
uv run ruff check .

# 运行类型检查
uv run mypy src

# 运行代码格式化
uv run ruff format .
```

### 测试

项目使用单元测试和基于属性的测试：

```bash
# 运行所有测试
uv run pytest

# 仅运行单元测试
uv run pytest tests/unit

# 仅运行属性测试
uv run pytest tests/property -v --hypothesis-show-statistics

# 运行测试并生成覆盖率报告
uv run pytest --cov=heic2jpg --cov-report=html
```

## 质量验证与人工复核

当调整优化逻辑时，建议基于多场景真实样本验证，而不是只看单一案例。

推荐流程：

```bash
# 批量转换代表性样本目录
heic2jpg samples/*.HEIC samples/*.heic --output-dir /tmp/sample-output
```

- 对机器标记为风险或边缘可疑的图片做人工并排复核（输入 vs 输出）。
- 当自动指标与肉眼观感不一致时，以人工视觉判断为最终依据。
- 保留一份 `input -> output` 复核清单，便于最终验收。

## 文档

- [English Documentation](README.md) - 英文文档
- [AGENTS.md](AGENTS.md) - AI 代理指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

## 许可证

MIT 许可证 - 详见 LICENSE 文件
