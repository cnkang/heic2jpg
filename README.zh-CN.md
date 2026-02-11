# HEIC 转 JPG 转换器

一个将 iPhone HEIC 照片转换为高质量 JPG 格式的 Python 应用程序，专为银盐（模拟）打印优化。

## 功能特性

- **高质量**：默认质量 100（JPEG 最低压缩），确保最佳打印质量
- **逐图优化**：每张照片单独分析和优化
- **并行处理**：使用多个 CPU 核心快速批量转换
- **EXIF 保留**：保持原始文件的所有元数据
- **跨平台**：支持 macOS、Windows 和 Linux
- **智能调整**：处理具有挑战性的光照条件（过曝、逆光、弱光）

## 系统要求

- Python 3.14 或更高版本
- uv 包管理器

## 安装

```bash
# 如果还没有安装 uv，先安装它
pip install uv

# 克隆仓库
git clone https://github.com/yourusername/heic-to-jpg-converter.git
cd heic-to-jpg-converter

# 安装依赖
uv sync

# 以开发模式安装
uv pip install -e .
```

## 使用方法

```bash
# 转换单个文件
heic-converter input.heic

# 使用自定义质量转换
heic-converter input.heic --quality 95

# 批量转换目录
heic-converter *.heic --output-dir ./converted

# 批量转换且不覆盖现有文件
heic-converter *.heic --no-overwrite

# 详细日志输出
heic-converter input.heic --verbose

# 显示帮助
heic-converter --help

# 显示版本
heic-converter --version
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
uv run pytest --cov=heic_converter --cov-report=html
```

## 文档

- [English Documentation](README.md) - 英文文档
- [AGENTS.md](AGENTS.md) - AI 代理指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

## 许可证

MIT 许可证 - 详见 LICENSE 文件

## 状态

🚧 **开发中** - 该项目目前正在积极开发中。
