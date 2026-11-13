# Agent V1 Prototype

[English](#english) | [简体中文](#简体中文)

---

## English

A pragmatic, local-first AI Agent runtime built specifically for small language models (7B/9B). We don't build a magic AGI; we build robust engineering guardrails to help small models survive in real-world tasks.

> **⚠️ A Note on Honesty:** This is an experimental, architecture-focused open-source project, not a commercial product. It does not have kernel-level sandboxing, multi-agent swarms, or a plugin marketplace. It is a **single-process, highly decoupled** runtime.

### ✨ Core Features & Architecture

| Feature | Description |
| :--- | :--- |
| **Pure Atomic Tools** | Instead of writing dozens of format-specific plugins, we only provide `execute_python`, `execute_command`, `browser`, and `web_search`. The model is forced to compose its own logic. |
| **Decoupled LLM Backends** | The LLM factory pattern allows seamless switching between **Ollama**, native **llama.cpp**, and **Cloud APIs** (e.g., DeepSeek) without changing business logic. |
| **Dynamic RAG Memory** | Uses `fastembed` (pure Python, CPU-only) and ChromaDB for semantic retrieval. **Zero dimension conflicts.** We inject relevant knowledge only when the model needs it. |
| **Policy-Driven Guardrails** | Instead of hardcoded `if-else` blocks, we use a Strategy Pattern (`GuardrailEngine`) to intercept deadlocks, tool failures, and infinite loops. |
| **Local-First & Lightweight** | Runs entirely on your local machine. No mandatory Docker, no heavy external dependencies for memory vectorization. |

### 🧩 System Coupling & Design Philosophy
- **Decoupled OS Layer**: `core/sys_utils.py` abstracts cross-platform process management (`setsid` vs `taskkill`).
- **Decoupled Memory Layer**: SQLite for structural storage + ChromaDB for vector search, unified behind a `MemoryStore` interface.
- **Safety by Design**: Out-of-the-box blacklist interception for dangerous commands (`rm -rf /`, `curl | bash`) and strict `<untrusted_data>` encapsulation for all web scraping.
- **Graceful Degradation**: If the small model hallucinates or gets stuck in a loop, the `GuardrailEngine` will forcefully inject corrective prompts or terminate the task, rather than burning your GPU.

### 🚀 Quick Start

**For macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.sh | bash
```

**For Windows (PowerShell):**
```powershell
powershell -Command "iwr -usefl https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.bat -OutFile $env:TEMP\install.bat; & $env:TEMP\install.bat"
```

### ⚠️ Current Limitations (What we haven't solved yet)
- **No True Concurrency**: It operates in a single-process worker model. While it queues tasks, it does not support true multi-tenant parallel execution (due to local VRAM constraints).
- **No Kernel Sandboxing**: Security is enforced at the command-line regex and tool-execution level. It is not a Docker/KVM sandbox.
- **Limited Multi-agent Capabilities**: Currently focused on a single, powerful assistant rather than orchestrating multiple sub-agents.

---

## 简体中文

一个务实、本地优先的 AI Agent 运行时，专为小模型（7B/9B）设计。我们不造 AGI 的梦，我们只做工程化的防呆机制，让小模型能在真实任务中活下来。

> **⚠️ 诚实声明**：这是一个专注于架构设计的实验性开源项目，并非商业级产品。它没有内核级沙箱、没有多智能体集群、没有插件市场。它是一个**单进程、高度解耦**的轻量级运行时。

### ✨ 核心特性与架构设计

| 特性 | 描述 |
| :--- | :--- |
| **纯原子工具** | 拒绝“胶水代码”。我们只提供 `execute_python`、`execute_command` 等最基础的触手，逼迫模型自己写代码，而不是依赖大量死板的专用工具。 |
| **多后端解耦** | 依赖工厂模式，可以在 **Ollama**、原生 **llama.cpp** 和 **云端 API**（如 DeepSeek）之间无缝切换，业务代码零修改。 |
| **动态 RAG 记忆** | 彻底抛弃复杂的 Ollama 向量依赖，全量采用 `fastembed`（纯 CPU、轻量、512维）。**彻底解决维度冲突问题**。按需注入，不污染上下文。 |
| **策略型护栏 (Guardrails)** | 抛弃在主循环里写死 `if-else`，重构为策略模式。防死循环、防连续失败、静默知识注入全由独立的护栏类接管。 |
| **本地优先与极简** | 数据完全不离开本地。不需要额外部署重型向量库，Python 环境一键拉起。 |

### 🧩 系统解耦程度与设计哲学
- **操作系统层解耦**：`core/sys_utils.py` 完美抹平了 Linux 与 Windows 在进程组强杀上的差异。
- **存储层解耦**：SQLite 存正文，ChromaDB 存向量，对外暴露统一的 `MemoryStore` 接口。
- **设计级安全**：内置高危命令黑名单拦截，且对所有外部抓取的网页数据强制包裹 `<untrusted_data>`，防止提示词注入。
- **优雅降级**：如果小模型陷入死循环，护栏引擎会强制注入纠偏提示词，或者直接强行终止任务，保护你的显存不被烧干。

### 🚀 极简安装

**macOS / Linux 用户：**
```bash
curl -fsSL https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.sh | bash
```

**Windows 用户（PowerShell）：**
```powershell
powershell -Command "iwr -usefl https://raw.githubusercontent.com/3344345/agent_v1pro/main/install.bat -OutFile $env:TEMP\install.bat; & $env:TEMP\install.bat"
```

### ⚠️ 已知限制（我们尚未解决的问题）
- **并非真正的并发**：目前是单 Worker 排队模式。受限于本地显存，无法像云端服务那样高并发处理请求。
- **无内核级沙箱**：安全依赖命令正则拦截和执行器隔离，并非完整的 Docker/KVM 沙箱。
- **非多智能体系统**：目前专注于打造单一强力助手，暂不支持多 Agent 通讯编排。
