#!/bin/bash
# ==============================================================
# Agent V1 Pro - 智能启动脚本 (带环境与模型自检)
# 用法:
#   ./run.sh          启动 网页端 + 终端 CLI（默认）
#   ./run.sh web      只启动网页端（后台）
#   ./run.sh cli      只启动终端 CLI（网页端若没起会自动带起）
#   ./run.sh stop     停止后台网页端
# 可用环境变量覆盖: AGENT_WEB_HOST / AGENT_WEB_PORT
# ==============================================================

# 1. 确保在项目根目录下运行
cd "$(dirname "$0")" || exit 1

# 2. 自动加载 .env 环境变量
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

MODE="${1:-all}"
WEB_HOST="${AGENT_WEB_HOST:-127.0.0.1}"
WEB_PORT="${AGENT_WEB_PORT:-8124}"
WEB_URL="http://$WEB_HOST:$WEB_PORT"
WEB_LOG="logs/web.log"
WEB_PID_FILE="runtime/web.pid"
mkdir -p logs runtime

echo "──────────────────────────────────────────"
echo " venv    : $PYTHON_BIN"
echo " mode    : $MODE"
echo " web     : $WEB_URL"
echo " backend : ${AGENT_LLM_BACKEND:-llamacpp_server}"
echo " planner : ${PLANNER_MODEL:-qwen2.5:7b}"
echo " router  : ${ROUTER_MODEL:-qwen2.5:1.5b-instruct}"
echo " embed   : ${EMBED_MODEL:-bge-m3}"
echo " log     : $(pwd)/logs/agent.jsonl"
echo "──────────────────────────────────────────"

web_alive() {
    curl -s -m 2 -o /dev/null "$WEB_URL/api/status" 2>/dev/null
}

stop_web() {
    local pid
    if [ -f "$WEB_PID_FILE" ]; then
        pid="$(cat "$WEB_PID_FILE" 2>/dev/null)"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "🛑 已停止网页端 (pid $pid)"
            rm -f "$WEB_PID_FILE"
            return 0
        fi
        rm -f "$WEB_PID_FILE"
    fi
    if web_alive; then
        echo "⚠️ $WEB_URL 上还有响应，但找不到本脚本记录的 pid，请手动检查:"
        ss -ltnp 2>/dev/null | grep ":$WEB_PORT"
    else
        echo "ℹ️ 网页端未在运行"
    fi
}

start_web() {
    if web_alive; then
        echo "ℹ️ 网页端已在运行: $WEB_URL"
        return 0
    fi
    if ss -ltn 2>/dev/null | grep -q ":$WEB_PORT "; then
        echo "❌ 端口 $WEB_PORT 已被其他进程占用，无法启动网页端："
        ss -ltnp 2>/dev/null | grep ":$WEB_PORT"
        return 1
    fi
    nohup "$PYTHON_BIN" web/server.py --host "$WEB_HOST" --port "$WEB_PORT" >> "$WEB_LOG" 2>&1 &
    echo $! > "$WEB_PID_FILE"
    local i
    for i in $(seq 1 30); do
        web_alive && break
        sleep 0.5
    done
    if web_alive; then
        echo "🌐 网页端已启动: $WEB_URL   (日志: $WEB_LOG)"
        return 0
    fi
    echo "❌ 网页端启动失败，最近日志："
    tail -n 20 "$WEB_LOG" 2>/dev/null
    return 1
}

case "$MODE" in
    stop)
        stop_web
        exit 0
        ;;
    web|all|cli) ;;
    *)
        echo "❌ 未知模式: $MODE   (可选: all | web | cli | stop)"
        exit 2
        ;;
esac

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

# 5. 启动网页端
start_web || echo "⚠️ 网页端未能启动，终端 CLI 仍可继续使用。"

if [ "$MODE" == "web" ]; then
    echo "✅ 网页端就绪，浏览器打开: $WEB_URL"
    echo "   停止请执行: ./run.sh stop"
    exit 0
fi

# 6. 启动主程序（终端 CLI）
echo "🚀 正在启动 Agent (CLI)..."
$PYTHON_BIN main.py
CLI_RC=$?
echo "👋 Agent 已退出 (code $CLI_RC)；网页端仍在后台运行，停止请执行: ./run.sh stop"
exit $CLI_RC
