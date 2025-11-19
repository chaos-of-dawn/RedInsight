#!/bin/bash

# RedInsight 启动脚本 (Linux/Mac)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "   RedInsight 启动程序"
echo "========================================"
echo ""

# 获取脚本所在目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 错误：虚拟环境不存在${NC}"
    echo ""
    echo "请先运行 ./install.sh 完成安装"
    echo ""
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 错误：无法激活虚拟环境${NC}"
    echo ""
    exit 1
fi

# 检查Streamlit是否安装
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 错误：Streamlit未安装${NC}"
    echo ""
    echo "请先运行 ./install.sh 完成安装"
    echo ""
    exit 1
fi

# 检查端口是否被占用
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  警告：端口8501已被占用${NC}"
    echo "   另一个RedInsight实例可能正在运行"
    echo ""
    read -p "是否继续启动（将使用其他端口）? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消启动"
        exit 0
    fi
fi

# 激活检查（在启动Streamlit之前）
echo ""
echo -e "${BLUE}[INFO] 检查激活状态...${NC}"
python -c "import sys; sys.path.insert(0, '.'); from activation import check_and_activate; import sys; sys.exit(0 if check_and_activate() else 1)"
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 错误：激活失败或需要激活${NC}"
    echo ""
    echo "请完成激活后再启动应用"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ 激活验证通过${NC}"
echo ""

# 启动应用
echo ""
echo -e "${GREEN}🚀 正在启动RedInsight...${NC}"
echo ""
echo "📊 访问地址: http://localhost:8501"
echo "💡 提示：浏览器将自动打开"
echo "⏹️  按 Ctrl+C 可停止应用"
echo ""

# 检测操作系统并打开浏览器
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sleep 3 && xdg-open http://localhost:8501 >/dev/null 2>&1 &
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sleep 3 && open http://localhost:8501 >/dev/null 2>&1 &
fi

# 启动Streamlit
streamlit run streamlit_app.py --server.headless=false --server.port=8501

# 如果退出，显示提示
echo ""
echo -e "${GREEN}✅ 应用已停止${NC}"

