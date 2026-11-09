#!/bin/bash
# ==============================================================
# Agent V1 Pro - 智能启动脚本 (带环境与模型自检)
# ==============================================================

# 1. 确保在项目根目录下运行
cd "$(dirname "$0")" || exit 1

# 2. 自动加载 .env 环境变量
# 替换为这段：
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# 3. 基础路径配置
PYTHON_BIN=".venv/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ 错误: 未找到虚拟环境 (.venv)。"
    echo "👉 请先运行 ./install.sh 完成初始化。"
    exit 1
fi

echo "──────────────────────────────────────────"
echo " venv    : $PYTHON_BIN"
echo " backend : ${AGENT_LLM_BACKEND:-llamacpp_server}"
echo " planner : ${PLANNER_MODEL:-qwen2.5:7b}"
echo " router  : ${ROUTER_MODEL:-qwen2.5:1.5b-instruct}"
echo " embed   : ${EMBED_MODEL:-bge-m3}"
echo " log     : $(pwd)/logs/agent.jsonl"
echo "──────────────────────────────────────────"

# 4. 针对 Ollama 的深度自检
if [ "$AGENT_LLM_BACKEND" == "ollama" ]; then
    if ! command -v ollama &>/dev/null; then
        echo "❌ 错误: 未找到 ollama 命令。请先安装 Ollama。"
        exit 1
    fi

    # 检查 Ollama 服务是否存活
    if ! curl -s http://localhost:11434/api/tags >/dev/null; then
        echo "⚠️ Ollama 服务未启动，正在尝试唤醒..."
        if [[ "$(uname -s)" == "Darwin" ]]; then
            open -a Ollama
        else
            ollama serve >/dev/null 2>&1 &
        fi
        
        # 等待最多 10 秒
        for i in {1..10}; do
            if curl -s http://localhost:11434/api/tags >/dev/null; then
                break
            fi
            sleep 1
        done
    fi

    # 检查三个模型是否就位
    echo "🔍 正在检查本地模型库..."
    OLLAMA_LIST=$(ollama list)
    
    # 提取模型名称（去除环境变量中的版本标签以便单纯匹配，或者直接严格匹配）
    check_model() {
        local model_name=$1
        local role=$2
        if [[ "$OLLAMA_LIST" != *"$model_name"* ]]; then
            echo "❌ 缺少 $role 模型: $model_name"
            echo "👉 请在终端运行: ollama pull $model_name"
            exit 1
        fi
    }

    check_model "${PLANNER_MODEL:-qwen2.5:7b}" "Planner (主模型)"
    check_model "${ROUTER_MODEL:-qwen2.5:1.5b-instruct}" "Router (路由模型)"
    check_model "${EMBED_MODEL:-bge-m3}" "Embedder (向量模型)"
    
    echo "✅ 核心模型检查通过！"
fi

# 5. 启动主程序
echo "🚀 正在启动 Agent..."
$PYTHON_BIN main.py