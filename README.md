# Agent V1 Pro

[English](#english) | [简体中文](#简体中文)

---

## English

A local-first, multi-backend AI Agent runtime exploring long-term memory, self-correction, and basic guardrails for local small language models.

### ✨ Features

- **Multi-Backend Support**: Supports switching between local deployment via **Ollama**, native **llama.cpp**, and pure **Cloud API** (e.g., DeepSeek).
- **Lightweight Memory**: Cloud mode optionally uses `fastembed` for local vector retrieval, eliminating the dependency on deploying a local Ollama instance for memory features.
- **Logs as History**: Simplifies the architecture by extracting action sequences directly from JSONL logs instead of maintaining redundant database tables.
- **Cross-Platform**: Initial adaptations for Linux, macOS, and Windows, including a basic graphical installation wizard.
- **Guardrails & Interventions**: Includes basic context shrinking, tool failure interventions, and prompt constraints to mitigate memory pollution and infinite loops.

### ⚠️ Critical Warning: Embedding Dimension Conflict

This system uses ChromaDB for long-term memory. **Switching the `EMBED_BACKEND` will cause a vector dimension mismatch!**
- **Ollama** (`bge-m3`) produces 1024-dim vectors.
- **Cloud / fastembed** produces 512-dim vectors.

If you must switch between these backends, you **MUST** clear the old memory database first:
```bash
rm -rf data/chroma
```

### 🚀 Quick Start

#### 1. One-Line Install (Recommended)

**For macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.sh | bash
```

**For Windows (PowerShell):**
```powershell
powershell -Command "iwr -usefl https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.bat -OutFile $env:TEMP\install.bat; & $env:TEMP\install.bat"
```
*The wizard will automatically handle the environment, dependencies, and guide you through backend selection.*

#### 2. Manual Installation
```bash
git clone https://github.com/3344345/agent_v1pro.git
cd agent_v1pro

# macOS / Linux
chmod +x install.sh
./install.sh

# Windows
# Double-click install.bat or run it in cmd
```

#### 3. Start the Agent
```bash
./run.sh
```

### 🛠️ Maintenance

Manage your memory (list, search, delete):
```bash
source .venv/bin/activate
python scripts/memory_admin.py list
```

---

## 简体中文

一个本地优先、多后端支持的 AI Agent 运行时，主要探索本地小模型在长期记忆、自我纠错和基础防线上的工程化落地。

### ✨ 核心特性

- **多后端引擎**：支持在 **Ollama** 本地部署、原生 **llama.cpp** 以及纯 **云端 API**（如 DeepSeek）之间切换。
- **轻量化记忆**：云端模式下可选择使用 `fastembed` 进行本地向量检索，省去了为了记忆功能而额外部署本地 Ollama 的麻烦。
- **日志即历史**：简化架构，直接从 JSONL 日志中提取动作序列作为上下文，去除了多余的流水表依赖。
- **跨平台兼容**：对 Linux、macOS 与 Windows 做了初步适配，并提供了基础的图形化配置向导。
- **基础防呆机制**：内置了基础的上下文压缩、工具失败干预与反思约束，用于缓解记忆污染和死循环问题。

### ⚠️ 重要警告：向量维度冲突

本系统使用 ChromaDB 存储长期记忆。**切换 `EMBED_BACKEND` 会导致向量维度不匹配直接崩溃！**
- **Ollama** (`bge-m3`) 产生 1024 维向量。
- **云端 / fastembed** 产生 512 维向量。

如果你必须在两套引擎间切换，请**务必**在终端执行以下命令清空旧记忆库：
```bash
rm -rf data/chroma
```

### 🚀 极简安装

#### 1. 一行命令安装（推荐）

**macOS / Linux 用户：**
```bash
curl -fsSL https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.sh | bash
```

**Windows 用户（打开 PowerShell）：**
```powershell
powershell -Command "iwr -usefl https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.bat -OutFile $env:TEMP\install.bat; & $env:TEMP\install.bat"
```
*安装向导会自动处理 Python 环境、依赖包，并弹出窗口让你选择后端和下载模型。*

#### 2. 手动克隆安装
```bash
git clone https://github.com/3344345/agent_v1pro.git
cd agent_v1pro

# macOS / Linux 用户
chmod +x install.sh
./install.sh

# Windows 用户
# 直接双击运行 install.bat 即可
```

#### 3. 启动 Agent
```bash
./run.sh
```

### 🛠️ 记忆维护

查看、搜索或删除记忆库中的条目：
```bash
source .venv/bin/activate
python scripts/memory_admin.py list
```

---
*Powered by the philosophy of "Pure Atomic Tools" and "Logs as History".*