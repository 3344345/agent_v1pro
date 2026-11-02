#!/usr/bin/env bash

# ==============================================================
# Agent V1 Pro - 智能引导安装脚本 (Bootstrap)
# ==============================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       📦 Agent V1 Pro 环境部署与配置向导${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. 环境分流：在线流 vs 离线本地运行
if [ -t 0 ]; then
    echo -e "${BLUE}📦 检测到本地离线安装模式...${NC}"
    SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    echo -e "${BLUE}🌐 检测到在线拉取安装模式...${NC}"
    SOURCE_DIR="$HOME/.local/share/AgentV1Pro"
    mkdir -p "$SOURCE_DIR"
    echo -e "${YELLOW}⬇️  正在拉取最新代码...${NC}"
    git clone --depth 1 https://github.com/你的仓库地址.git "$SOURCE_DIR" || true
fi

cd "$SOURCE_DIR" || exit 1

echo -e "\n${BLUE}[1/3] 正在检查 Python 环境...${NC}"
OS="$(uname -s)"

check_python_version() {
    if command -v python3 &>/dev/null; then
        python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" &>/dev/null
        return $?
    fi
    return 1
}

install_python_macos() {
    echo -e "${YELLOW}⚠️ 未找到合适的 Python3，正在尝试自动拉取官方安装包...${NC}"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        PY_URL="https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
    else
        PY_URL="https://www.python.org/ftp/python/3.11.9/python-3.11.9-macosx10.9.pkg"
    fi
    
    echo -e "⬇️  正在下载: $PY_URL"
    if curl -L --connect-timeout 10 -o /tmp/python-installer.pkg "$PY_URL"; then
        echo -e "🔐 需要管理员权限来安装 Python，请输入密码:"
        sudo xattr -d com.apple.quarantine /tmp/python-installer.pkg 2>/dev/null || true
        if sudo installer -pkg /tmp/python-installer.pkg -target /; then
            rm -f /tmp/python-installer.pkg
            export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"
            echo -e "${GREEN}✅ Python 3.11 自动安装成功！${NC}"
            return 0
        fi
    fi

    echo -e "\n${YELLOW}⚠️ 自动安装未能完成，为你打开官方网页下载。${NC}"
    open "https://www.python.org/downloads/macos/"
    exit 1
}

if check_python_version; then
    PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}✅ 检测到可用的 Python3 (版本 ${PY_VER})。${NC}"
else
    if [[ "$OS" == "Darwin" ]]; then
        install_python_macos
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt &>/dev/null; then sudo apt update && sudo apt install -y python3 python3-venv python3-tk;
        elif command -v dnf &>/dev/null; then sudo dnf install -y python3 python3-pip python3-tkinter;
        elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm python tk; fi
        if ! check_python_version; then exit 1; fi
    fi
fi

echo -e "\n${BLUE}[2/3] 检查图形界面依赖 (Tkinter)...${NC}"
if ! python3 -c "import tkinter" &>/dev/null; then
    if [[ "$OS" == "Darwin" ]]; then
        echo -e "${RED}❌ macOS 官方 Python 自带 Tkinter。请检查环境变量。${NC}"
        exit 1
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt &>/dev/null; then sudo apt install -y python3-tk;
        elif command -v dnf &>/dev/null; then sudo dnf install -y python3-tkinter; fi
        if ! python3 -c "import tkinter" &>/dev/null; then exit 1; fi
    fi
else
    echo -e "${GREEN}✅ Tkinter 依赖正常。${NC}"
fi

echo -e "\n${BLUE}[3/3] 环境准备完毕！拉起图形界面...${NC}"
if [[ -f "install_gui.py" ]]; then
    python3 install_gui.py
else
    echo -e "${RED}❌ 未找到 install_gui.py，请检查文件完整性。${NC}"
    exit 1
fi