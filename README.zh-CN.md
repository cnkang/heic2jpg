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
heic-converter --version
```

安装完成后，`heic-converter` 命令就可以在任何目录使用了。

### 快速测试

```bash
# 测试转换（假设你有一个 test.heic 文件）
heic-converter test.heic

# 如果没有 HEIC 文件，可以先运行测试确保一切正常
uv run pytest tests/unit -v
```

## 使用方法

### 单文件转换

```bash
# 转换单个文件（输出到同一目录）
heic-converter photo.heic

# 使用自定义质量转换
heic-converter photo.heic --quality 95

# 转换到指定目录
heic-converter photo.heic --output-dir ./converted
```

### 批量转换同一目录下的所有 HEIC 文件

```bash
# 方法 1: 使用通配符（推荐）
heic-converter *.heic

# 方法 2: 使用通配符并指定输出目录
heic-converter *.heic --output-dir ./converted

# 方法 3: 明确指定多个文件
heic-converter photo1.heic photo2.heic photo3.heic

# 方法 4: 批量转换且不覆盖已存在的文件
heic-converter *.heic --no-overwrite

# 方法 5: 批量转换并显示详细日志
heic-converter *.heic --verbose
```

### 高级用法

```bash
# 批量转换，自定义质量，输出到指定目录
heic-converter *.heic --quality 95 --output-dir ./converted

# 批量转换，不覆盖现有文件，显示详细日志
heic-converter *.heic --no-overwrite --verbose

# 显示帮助信息
heic-converter --help

# 显示版本信息
heic-converter --version
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
heic-converter *.heic

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
heic-converter *.heic --output-dir ./converted

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
