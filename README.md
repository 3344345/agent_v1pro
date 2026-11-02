# Agent V1 Pro

[English](#english) | [简体中文](#简体中文)

---

## English

A local-first, multi-engine AI Agent runtime featuring long-term memory, self-correction mechanisms, and anti-deadlock defenses.

### ✨ Features

- **Multi-Backend Support**: Seamlessly switch between local deployment via **Ollama**, native **llama.cpp**, and pure **Cloud API** (e.g., DeepSeek).
- **Lightweight Memory**: Cloud mode uses `fastembed` for zero-Ollama-dependency local vector retrieval.
- **Logs as History**: Abandons redundant database tables; mechanically extracts action sequences with timestamps directly from logs.
- **Cross-Platform**: Fully compatible with Linux, macOS, and Windows. Includes a bilingual GUI installation wizard.
- **Anti-Hallucination & Deadlocks**: Context shrinking, tool failure intervention, and strict reflection prompts to prevent memory pollution.

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

本地优先、多引擎驱动、具备长期记忆与自我防暴走机制的智能 Agent 运行时。

### ✨ 核心特性

- **多后端引擎**：完美支持 **Ollama** 本地部署、原生 **llama.cpp** 以及纯 **云端 API**（如 DeepSeek）。
- **轻量化记忆**：云端模式采用 `fastembed` 实现零 Ollama 依赖的本地向量检索，纯 CPU 运行。
- **日志即历史**：废弃冗余数据库流水表，直接从 JSONL 日志提取带时间戳的动作序列作为上下文。
- **跨平台兼容**：完美适配 Linux、macOS 与 Windows，提供中英双语的图形化配置向导。
- **防暴走与防幻觉**：内置上下文压缩、工具失败干预与严格的反思 Prompt，防止记忆污染。

### ⚠️ 重要警告：向量维度冲突

本系统使用 ChromaDB 存储长期记忆。**切换 `EMBED_BACKEND` 会导致向量维度不匹配直接崩溃！**
- **Ollama** (`bge-m3`) 产生 1024 维向量。
- **云端 / fastembed** 产生 512 维向量。

如果你必须在两套引擎间切换，请**务必**在终端执行以下命令清空旧记忆库：
```bash
rm -rf data/chroma
```

### 🚀 极简安装

#### 1. 一行命令极速安装（推荐）

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