#!/bin/bash

# 准备离线安装包脚本（给开发者使用）

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "========================================"
echo "   准备离线安装包（给开发者使用）"
echo "========================================"
echo ""
echo "此脚本将下载所有依赖包到本地，用于完全离线安装"
echo ""

# 获取脚本所在目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 检查Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 错误：未检测到Python"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 创建离线包目录
OFFLINE_DIR="$PROJECT_DIR/offline_packages"
mkdir -p "$OFFLINE_DIR"

echo "📦 开始下载依赖包到: $OFFLINE_DIR"
echo "   这可能需要10-20分钟，取决于网络速度..."
echo ""

# 下载所有依赖包
$PYTHON_CMD -m pip download -r requirements.txt -d "$OFFLINE_DIR" --python-version 3.10

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 下载失败，请检查网络连接和requirements.txt文件"
    exit 1
fi

# 统计文件数量
COUNT=$(ls -1 "$OFFLINE_DIR"/*.whl 2>/dev/null | wc -l)

echo ""
echo "========================================"
echo "   ✅ 离线包准备完成！"
echo "========================================"
echo ""
echo "📊 统计信息："
echo "   下载文件数: $COUNT 个"
echo "   存储路径: $OFFLINE_DIR"
echo ""
echo "💡 使用方法："
echo "   1. 将 offline_packages 文件夹一起打包"
echo "   2. 在其他电脑上运行 install.sh 即可自动检测并使用"
echo ""

