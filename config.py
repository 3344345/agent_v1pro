import os
import sys
import platform

# ==============================================================================
# 基础路径配置
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "agent.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ==============================================================================
# 操作系统与 Shell 环境解耦
# ==============================================================================
OS_SYSTEM = platform.system()
if OS_SYSTEM == "Darwin":
    EXEC_SHELL = "/bin/zsh"
    MPL_FONT_FAMILY = "PingFang SC"
elif OS_SYSTEM == "Windows":
    EXEC_SHELL = "powershell.exe"
    MPL_FONT_FAMILY = "Microsoft YaHei"
else:
    EXEC_SHELL = "/bin/bash"
    MPL_FONT_FAMILY = "Noto Sans CJK SC"

# ==============================================================================
# 模型后端选择
# ==============================================================================
LLM_BACKEND = os.environ.get("AGENT_LLM_BACKEND", "llamacpp_server")
ROUTER_BACKEND = os.environ.get("AGENT_ROUTER_BACKEND", LLM_BACKEND)

# ==============================================================================
# 云端 API 配置
# ==============================================================================
CLOUD_API_BASE = os.environ.get("AGENT_API_BASE", "https://api.deepseek.com/v1")
CLOUD_API_KEY = os.environ.get("AGENT_API_KEY", "your-api-key-here")
CLOUD_MODEL_NAME = os.environ.get("AGENT_CLOUD_MODEL", "deepseek-chat")

# ------------------------------------------------------------------------------
# 云端「思考模式」开关（仅 cloud_api 后端生效，本地 llama.cpp/9B 不受影响）
#   "disabled" → 请求里带 thinking={"type":"disabled"}，不返回 reasoning_content
#                推荐：Agent 工具调用场景延迟低，且彻底规避 reasoning 回传 400
#   "enabled"  → 保持默认思考模式，代码会自动把所有历史 assistant 消息的
#                reasoning_content 原样回传（缺失的补空串），同样不会 400
# 环境变量：AGENT_CLOUD_THINKING=enabled 可临时切换
CLOUD_THINKING = os.environ.get("AGENT_CLOUD_THINKING", "disabled")


# ==============================================================================
# Ollama 本地后端配置
# ==============================================================================
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TIMEOUT = 600

# ==============================================================================
# Planner (执行大脑)
# ==============================================================================
LLAMACPP_BIN   = os.environ.get("LLAMACPP_BIN", os.path.expanduser("~/projects/llama.cpp/build/bin/llama-server"))
LLAMACPP_MODEL = os.environ.get("LLAMACPP_MODEL", os.path.expanduser("~/models/qwen3.5-9b.gguf"))
LLAMACPP_HOST  = os.environ.get("LLAMACPP_HOST", "127.0.0.1")
LLAMACPP_PORT  = int(os.environ.get("LLAMACPP_PORT", 8081))
LLAMACPP_URL   = f"http://{LLAMACPP_HOST}:{LLAMACPP_PORT}"
LLAMACPP_CTX   = int(os.environ.get("LLAMACPP_CTX", 102400))   # 必须与 llama-server 的 --ctx-size 一致（8G 显存 + FA + Q8 KV 实测可跑 32K）
LLAMACPP_NGL   = 99
LLAMACPP_PARALLEL = 1
LLAMACPP_TIMEOUT = 600
LLAMACPP_KV_QUANT = False 
LLAMACPP_REASONING = "off"
LLAMACPP_REASONING_BUDGET = 0
LLAMACPP_CHAT_TEMPLATE_KWARGS = '{"enable_thinking": false}'

# ==============================================================================
# Router (路由翻译官)
# ==============================================================================
ROUTER_SERVER_BIN   = LLAMACPP_BIN
ROUTER_SERVER_MODEL = os.environ.get("ROUTER_SERVER_MODEL", os.path.expanduser("~/models/qwen2.5-1.5b-instruct.gguf"))
ROUTER_SERVER_HOST  = os.environ.get("ROUTER_SERVER_HOST", "127.0.0.1")
ROUTER_SERVER_PORT  = int(os.environ.get("ROUTER_SERVER_PORT", 8082))
ROUTER_SERVER_URL   = f"http://{ROUTER_SERVER_HOST}:{ROUTER_SERVER_PORT}"
ROUTER_SERVER_CTX   = 4096
ROUTER_SERVER_NGL   = 0
ROUTER_SERVER_PARALLEL = 1
ROUTER_SERVER_TIMEOUT  = 120
ROUTER_SERVER_REASONING = "off"
ROUTER_SERVER_REASONING_BUDGET = 0
ROUTER_SERVER_CHAT_TEMPLATE_KWARGS = '{"enable_thinking": false}'

# ==============================================================================
# 网络搜索配置
# ==============================================================================
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080/search")
SEARCH_BACKENDS = ["parallel"]
SEARCH_SOURCE_ALIASES = {"parallel": "parallel", "searxng": "searxng", "web": "parallel", "网络": "parallel", "本地": "searxng", "local": "searxng"}

# ==============================================================================
# 浏览器与自动化配置
# ==============================================================================
CHROME_BIN = os.environ.get("CHROME_BIN", "")
CHROME_PORT = 9222
CHROME_USER_DATA = "/tmp/chrome-debug"
CHROME_STDOUT_LOG = "/tmp/chromium_stdout.log"
CHROME_STDERR_LOG = "/tmp/chromium_stderr.log"
BROWSER_PROFILE_DIR = os.path.join(DATA_DIR, "browser-profile")
BROWSER_HEADLESS = False
BROWSER_TIMEOUT = 30000

# ==============================================================================
# 核心防暴走与熔断机制配置
# ==============================================================================
MAX_ATTEMPTS = 50
FAILURE_THRESHOLD = 5
SAME_CALL_THRESHOLD = 3
ENABLE_LOG_ROTATION = True
ROUTER_MODEL = "qwen2.5:1.5b-instruct"
PLANNER_MODEL = "qwen3.5:9b"

# ==============================================================================
# 上下文压缩与历史记录管理
# ==============================================================================
HISTORY_LIMIT = 12
COMPRESS_KEEP_RECENT = 8
COMPRESS_MAX_CHARS = 300
HISTORY_RESULT_TRUNCATE = 200
TURN_HISTORY_MAX = 100

# ==============================================================================
# 上下文预算（按真实 token 窗口换算，禁止再写死字符数）
# ==============================================================================
# 唯一的"真值"是 CONTEXT_WINDOW_TOKENS = 推理端的 --ctx-size。
# 其余系统提示/工具输出的字符上限全部由它派生，换模型或换 ctx 只改一处。
# 换算基准：ASCII（英文/代码）≈3 字符/token，CJK ≈1.4 字/token，取值偏保守。
CONTEXT_WINDOW_TOKENS = int(os.environ.get("AGENT_CTX_TOKENS", LLAMACPP_CTX))
OUTPUT_RESERVE_TOKENS = int(os.environ.get("AGENT_OUTPUT_RESERVE_TOKENS", 3072))  # 留给模型生成
PROMPT_BUDGET_TOKENS  = max(CONTEXT_WINDOW_TOKENS - OUTPUT_RESERVE_TOKENS, 1024)
CHARS_PER_TOKEN       = 1.6
PROMPT_BUDGET_CHARS   = int(PROMPT_BUDGET_TOKENS * CHARS_PER_TOKEN)

SYSTEM_BUDGET_TOKENS = int(PROMPT_BUDGET_TOKENS * 0.50)   # 系统提示不超过 prompt 预算的一半，另一半留给历史/工具结果
SYS_HEAD_RATIO       = 0.20                               # 系统提示超预算时，头部保留比例（尾部更重要）
MAX_SYS_CHARS        = int(PROMPT_BUDGET_CHARS * 0.50)    # 由预算派生，仅供日志/兼容旧引用
MAX_OUTPUT_CHARS     = int(PROMPT_BUDGET_CHARS * 0.25)    # 单条工具输出上限，由预算派生

# ==============================================================================
# LLM 推理参数
# ==============================================================================
# num_predict 必须小于窗口（旧值 16384 等于整个 ctx，会把 prompt 挤没）
PLANNER_OPTIONS = {"temperature": 0.1, "num_predict": OUTPUT_RESERVE_TOKENS,
                   "num_ctx": CONTEXT_WINDOW_TOKENS, "top_p": 0.9, "think": False}
ROUTER_OPTIONS = {"temperature": 0.0, "num_predict": 200, "num_ctx": ROUTER_SERVER_CTX, "think": False}

# ==============================================================================
# Embedding (向量化) 配置
# ==============================================================================
EMBED_BACKEND = "llamacpp_direct"
EMBED_MODEL_PATH = os.environ.get("EMBED_MODEL_PATH", os.path.expanduser("~/models/bge-m3-Q8_0.gguf"))
EMBED_DIMENSION = 1024
EMBED_N_GPU_LAYERS = 0
EMBED_N_CTX = 512

# ==============================================================================
# 向量数据库与检索配置
# ==============================================================================
VECTOR_BACKEND = "chromadb"
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
CHROMA_COLLECTION = "memories"
MEMORY_TOP_K = 3
MEMORY_MIN_SCORE = 0.5

# ==============================================================================
# 输出目录
# ==============================================================================
OUTPUT_DIR = os.environ.get("AGENT_OUTPUT_DIR", os.path.join(os.path.expanduser("~"), "Desktop"))
SCREENSHOT_DIR = os.environ.get("AGENT_SCREENSHOT_DIR", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))

# ==============================================================================
# 🚨 上下文组装与 RAG 强干预配置（新版必须依赖这块）
# ==============================================================================
ANCHOR_TURNS_LIMIT = 10            # 任务锚点读取历史轮数
SUMMARY_READ_LIMIT = 3            # 历史摘要读取条数
RECENT_TURNS_LIMIT = 5            # 最近历史详情读取轮数
HISTORY_STEP_LIMIT = 6            # 每轮保留的步骤数量（超过则中间省略）
SKILL_MIN_SCORE = 0.3             # 强制召回 Skill 的最低阈值
RAG_INTERVENE_TOP_K = 2           # 反思时系统自动检索本地手册的召回数量
RAG_INTERVENE_MIN_SCORE = 0.6     # 反思检索的最低相似度阈值
MAX_REFLECT_COUNT = 5             # 任务内最多允许触发几次阶段反思
# MAX_SYS_CHARS / MAX_OUTPUT_CHARS 见上文"上下文预算"区（按窗口 token 换算派生）

# 轮内压缩配置
SHRINK_KEEP_HEAD = 2
SHRINK_KEEP_TAIL = 6
SHRINK_MAX_CHARS = 300
SHRINK_MIN_CHARS = 600

# 相似度与死循环熔断配置
TOOL_FAIL_INTERVENE_THRESHOLD = 3
SIGNATURE_WINDOW_SIZE = 6
SIGNATURE_DUP_THRESHOLD = 3
SIMILARITY_WINDOW_SIZE = 5
SIMILARITY_ARGS_THRESHOLD = 1.0  # 只有参数完全一致才算重复
SIMILARITY_OUT_THRESHOLD = 1.0  # 只有输出完全一致才算重复
HISTORY_INVALID_MINUTES = 15
HISTORY_INJECT_LIMIT = 3

# 反思机制配置
REFLECT_MAX_LEN = 100
REFLECT_CAUSAL_WORDS = ["因为", "由于", "导致", "从而"]
REFLECT_CONTINUE_FLAG = "[继续执行]"
REFLECT_STOP_FLAG = "[终止任务]"

# 路由和计划拦截配置
DIALOGUE_KEYWORDS = ["你好", "谢谢", "你是谁", "怎么回事", "你是不是", "刚才干了啥"]
PLANNING_KEYWORDS = ["接下来打算", "下一步", "换种思路", "我准备", "接下来我"]

# 技能强匹配映射字典（按需扩展）
# config.py
# config.py
SKILL_TRIGGER_MAP = {
    # 网页底座
    "web": {
        "keywords": ["网页", "浏览器", "搜索", "点击", "填表", "打开网站"],
        "query": "网页自动化与复杂交互 搜索与点击"
    },
    # B站专属
    "bilibili": {
        "keywords": ["B站", "bilibili", "哔哩哔哩", "视频", "UP主"],
        "query": "B站 视频 搜索 点击 播放"
    },
    # 通用下载底座
    "download_core": {
        "keywords": ["下载", "download", "获取文件", "镜像", "保存"],
        "query": "文件下载通用法则与安全校验"
    },
    # Git 代码操作
    "git_core": {
        "keywords": ["git", "clone", "仓库", "源码", "拉取代码"],
        "query": "Git 原生操作指南"
    },
    # GitHub Release 产物下载
    "github_release": {
        "keywords": ["github下载", "release", "安装包", "jar", "exe", "产物"],
        "query": "GitHub Release 产物下载指南"
    },
    # PPT
    "ppt": {
        "keywords": ["ppt", "幻灯片", "演示文稿"],
        "query": "制作 PPT 演示文稿"
    }
}

# ==============================================================================
# 偏好记忆开关
# ==============================================================================
ENABLE_PREFERENCE_MEMORY = True
SYSTEM_PROMPT = f"""你是一个智能助手，用中文回答。回答简洁直接。
【系统环境】当前系统：{OS_SYSTEM}，默认 Shell：{EXEC_SHELL}。输出文件保存在 {OUTPUT_DIR}。"""
AGENT_LANG = os.environ.get("AGENT_LANG", "zh")
OCR_LANG = os.environ.get("AGENT_OCR_LANG", "ch")

# ==============================================================================
# 🖼️ 多模态（图像输入）配置 —— 只需要改这一段
# ==============================================================================
# 总开关：False = 前端不显示传图入口，后端也不接受图片
IMAGE_INPUT_ENABLED = True

# 承载方式：
#   base64 -> 内联 data URL（推荐，云端/本地通吃，无需公网）
#   url    -> 只传图片外链（后端自己下载，省带宽但要求 URL 可达）
IMAGE_INPUT_MODE = "base64"

# 单条消息最多几张图
IMAGE_MAX_COUNT = 3
# 单张原始体积上限（字节），超过就先压
IMAGE_MAX_BYTES = 6 * 1024 * 1024
# 长边像素上限（OpenAI 建议 1568；数字越大 token 越贵）
IMAGE_MAX_SIDE = 1568
# 重新压缩时的 JPEG 质量
IMAGE_JPEG_QUALITY = 85
# OpenAI 的 detail 档位：auto / low / high（本地后端会忽略该字段）
IMAGE_DETAIL = "auto"
# 预算占位：一张图按多少 token 估算（high 档实际约 1k~1.6k）
IMAGE_EST_TOKENS_PER_IMAGE = 1200

# ---- 各后端是否支持"看图" ----
#   cloud_api       : 标准 OpenAI 格式，支持 image_url（已实测通过）
#   llamacpp_server : 走 /v1/chat/completions，需要启动时加 --mmproj 视觉投影
#   ollama          : 需要 llava / qwen2.5-vl / minicpm-v 之类的视觉模型
#   llamacpp_direct : 直连底层，不支持，会自动降级为纯文本
VISION_BACKEND_SUPPORT = {
    "cloud_api": True,
    "llamacpp_server": True,
    "ollama": True,
    "llamacpp_direct": False,
}

# 模型名里出现这些关键字才认为"该模型确实能看图"（用于自动判定，避免把图发给纯文本模型）
VISION_MODEL_KEYWORDS = [
    # DeepSeek 官方：deepseek-flash 支持图片输入（旧名 deepseek-v4-flash-vision-exp 已下线）
    "deepseek-flash", "deepseek-v4-flash-vision", "deepseek-vl",
    "gpt-4o", "gpt-4.1", "gpt-5", "o3", "o4",
    "claude-3", "claude-4", "claude-sonnet", "claude-opus",
    "gemini", "qwen-vl", "qwen2-vl", "qwen2.5-vl", "qwen3-vl",
    "llava", "minicpm-v", "glm-4v", "glm-4.5v", "internvl",
    "doubao-vision", "step-1v", "pixtral", "molmo",
]

# ---- 小模型（如 9B）收紧策略 ----
# 参数量 <= 该值(B) 视为小模型：上下文更紧、视觉编码更慢
SMALL_MODEL_PARAM_B = 12
SMALL_MODEL_MAX_SIDE = 1024       # 小模型长边再压一档，省 token
SMALL_MODEL_IMAGE_MAX_COUNT = 1   # 小模型一次只喂一张
SMALL_MODEL_IMAGE_TOKEN_BUDGET = 1600  # 小模型给图片预留的预算上限

# True = 跳过模型名检查，强制认为当前模型能看图（你确认后端有视觉能力时打开）
VISION_FORCE = False

# 纯文本后端收到图片时的行为：True = 丢掉图片并告知模型"用户发了图但你看不到"
IMAGE_FALLBACK_NOTICE = True
