#!/bin/bash

# RedInsight 一键安装脚本 (Linux/Mac)
# 支持完全离线安装

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "   RedInsight 一键安装程序"
echo "========================================"
echo ""

# 获取脚本所在目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 检查Python是否安装
echo "[1/6] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo ""
        echo -e "${RED}❌ 错误：未检测到Python环境${NC}"
        echo ""
        echo "请先安装Python 3.8或更高版本："
        echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
        echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
        echo "  macOS: brew install python3"
        echo ""
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✅ 检测到Python版本: $PYTHON_VERSION${NC}"

# 检查Python版本
$PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 错误：Python版本过低（需要3.8+）${NC}"
    echo "   当前版本: $PYTHON_VERSION"
    echo ""
    exit 1
fi

# 创建虚拟环境
echo ""
echo "[2/6] 创建虚拟环境..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  检测到已存在的虚拟环境${NC}"
    read -p "是否重新创建？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 正在删除旧环境..."
        rm -rf venv
    else
        echo -e "${GREEN}✅ 使用现有虚拟环境${NC}"
        SKIP_VENV=true
    fi
fi

if [ "$SKIP_VENV" != "true" ]; then
    echo "📦 正在创建虚拟环境（这可能需要1-2分钟）..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ 错误：虚拟环境创建失败${NC}"
        echo "   请检查Python安装是否完整"
        echo ""
        exit 1
    fi
    echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
fi

# 激活虚拟环境并升级pip
echo ""
echo "[3/6] 准备安装环境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 错误：无法激活虚拟环境${NC}"
    echo ""
    exit 1
fi

pip install --upgrade pip --quiet
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  警告：pip升级失败，尝试继续安装...${NC}"
fi

# 检查离线依赖包
echo ""
echo "[4/6] 检查依赖包..."
OFFLINE_DIR="$PROJECT_DIR/offline_packages"
USE_OFFLINE=0

if [ -d "$OFFLINE_DIR" ] && [ -n "$(ls -A $OFFLINE_DIR/*.whl 2>/dev/null)" ]; then
    echo -e "${GREEN}✅ 检测到离线依赖包，将使用离线安装${NC}"
    USE_OFFLINE=1
    echo "📦 离线安装路径: $OFFLINE_DIR"
else
    echo -e "${YELLOW}⚠️  未检测到离线依赖包${NC}"
    echo "   将尝试在线安装（需要网络连接）"
    echo ""
    echo "💡 提示：如需完全离线安装，请先运行 prepare_offline_packages.sh"
fi

# 安装依赖
echo ""
echo "[5/6] 安装项目依赖（这可能需要3-5分钟）..."
echo "   请稍候，正在安装必要的组件..."

if [ "$USE_OFFLINE" == "1" ]; then
    # 离线安装
    echo "📦 使用离线包安装..."
    
    # 先安装wheel工具
    pip install wheel --quiet --no-index --find-links "$OFFLINE_DIR"
    
    # 按顺序安装PyTorch相关（如果存在）
    if ls "$OFFLINE_DIR"/torch*.whl 1> /dev/null 2>&1; then
        echo "    正在安装PyTorch..."
        pip install --quiet --no-index --find-links "$OFFLINE_DIR" torch torchvision 2>/dev/null || true
    fi
    
    # 安装其他依赖
    echo "    正在安装其他依赖包..."
    pip install --quiet --no-index --find-links "$OFFLINE_DIR" -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  离线安装遇到问题，尝试在线安装作为备选...${NC}"
        pip install -r requirements.txt --quiet
    fi
else
    # 在线安装
    if [ -f "requirements.txt" ]; then
        echo "    正在安装依赖包（需要网络连接）..."
        pip install -r requirements.txt --quiet
    fi
    
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ 错误：依赖安装失败${NC}"
        echo ""
        echo "可能的原因："
        echo "  1. 网络连接问题"
        echo "  2. PyPI服务器不可达"
        echo "  3. 缺少必要的编译工具（某些包需要）"
        echo ""
        echo "解决方案："
        echo "  1. 检查网络连接"
        echo "  2. 运行 prepare_offline_packages.sh 创建离线安装包"
        echo "  3. 重新运行本安装脚本"
        echo ""
        exit 1
    fi
fi

# 验证关键依赖
echo ""
echo "[6/6] 验证安装..."
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 错误：Streamlit安装验证失败${NC}"
    echo "   请检查安装过程是否有错误"
    exit 1
fi
echo -e "${GREEN}✅ Streamlit已安装${NC}"

python -c "import sqlalchemy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  警告：部分依赖可能未正确安装${NC}"
else
    echo -e "${GREEN}✅ 核心依赖验证通过${NC}"
fi

# 创建必要的目录
echo ""
echo "📁 创建必要的目录..."
mkdir -p output logs data vector_cache
echo -e "${GREEN}✅ 目录结构已创建${NC}"

# 完成
echo ""
echo "========================================"
echo "   ✅ 安装完成！"
echo "========================================"
echo ""
echo "📋 下一步操作："
echo "   1. 运行 ./start.sh 启动应用"
echo "   2. 首次使用需要在Web界面配置API密钥"
echo "   3. 配置完成后即可开始使用"
echo ""
echo "💡 提示："
echo "   - 启动后会自动打开浏览器"
echo "   - 按 Ctrl+C 可停止应用"
echo "   - 所有配置都通过Web界面完成，无需手动编辑文件"
echo ""

