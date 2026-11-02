#!/usr/bin/env bash

# ==============================================================
# Agent V1 Pro - 智能引导安装器 (Bootstrap)
# ==============================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       📦 Agent V1 Pro 安装引导${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. 判断安装模式
if [ -t 0 ]; then
    echo -e "${BLUE}📦 检测到本地安装模式...${NC}"
    INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    echo -e "${BLUE}🌐 检测到在线一键安装模式...${NC}"
    INSTALL_DIR="$HOME/.agent_v1pro"
    
    if ! command -v git &>/dev/null; then
        echo -e "${RED}❌ 错误: 未找到 git。请先安装 git 后再重试。${NC}"
        exit 1
    fi

    echo -e "${YELLOW}⬇️  正在拉取项目代码到 $INSTALL_DIR ...${NC}"
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR" && git pull
    else
        mkdir -p "$INSTALL_DIR"
        git clone https://github.com/3344345/agent_v1pro.git "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR" || exit 1
OS="$(uname -s)"

# 2. 检查 Python 环境 (>= 3.10)
check_python() {
    if command -v python3 &>/dev/null; then
        python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" &>/dev/null
        return $?
    fi
    return 1
}

if ! check_python; then
    echo -e "${YELLOW}⚠️ 未找到 Python 3.10+，尝试自动安装...${NC}"
    if [[ "$OS" == "Darwin" ]]; then
        PY_URL="https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
        if [[ "$(uname -m)" == "x86_64" ]]; then
            PY_URL="https://www.python.org/ftp/python/3.11.9/python-3.11.9-macosx10.9.pkg"
        fi
        curl -L -o /tmp/python.pkg "$PY_URL"
        sudo xattr -d com.apple.quarantine /tmp/python.pkg 2>/dev/null || true
        sudo installer -pkg /tmp/python.pkg -target /
        rm -f /tmp/python.pkg
        export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt &>/dev/null; then sudo apt update && sudo apt install -y python3 python3-venv python3-tk;
        elif command -v dnf &>/dev/null; then sudo dnf install -y python3 python3-pip python3-tkinter;
        elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm python tk; fi
    fi
fi

# 3. 检查 Tkinter
if ! python3 -c "import tkinter" &>/dev/null; then
    echo -e "${YELLOW}⚠️ 缺少图形界面依赖 (Tkinter)，正在尝试自动安装...${NC}"
    if [[ "$OS" == "Linux" ]]; then
        if command -v apt &>/dev/null; then sudo apt install -y python3-tk;
        elif command -v dnf &>/dev/null; then sudo dnf install -y python3-tkinter; fi
    fi
    if ! python3 -c "import tkinter" &>/dev/null; then
        echo -e "${RED}❌ Tkinter 安装失败，请手动安装 Python 官方包。${NC}"
        exit 1
    fi
fi

# 4. 拉起 GUI 并赋予 run.sh 执行权限
echo -e "${GREEN}✅ 基础环境就绪，正在启动图形化配置向导...${NC}\n"
chmod +x run.sh
python3 install_gui.py