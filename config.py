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
LLAMACPP_CTX   = 16384
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
BROWSER_TIMEOUT = 15000

# ==============================================================================
# 核心防暴走与熔断机制配置
# ==============================================================================
MAX_ATTEMPTS = 50
FAILURE_THRESHOLD = 5
SAME_CALL_THRESHOLD = 3
ENABLE_LOG_ROTATION = False
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
# LLM 推理参数
# ==============================================================================
PLANNER_OPTIONS = {"temperature": 0.1, "num_predict": 16384, "num_ctx": 16384, "top_p": 0.9, "think": False}
ROUTER_OPTIONS = {"temperature": 0.0, "num_predict": 200, "num_ctx": 4096, "think": False}

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
ANCHOR_TURNS_LIMIT = 3            # 任务锚点读取历史轮数
SUMMARY_READ_LIMIT = 3            # 历史摘要读取条数
RECENT_TURNS_LIMIT = 5            # 最近历史详情读取轮数
HISTORY_STEP_LIMIT = 6            # 每轮保留的步骤数量（超过则中间省略）
SKILL_MIN_SCORE = 0.3             # 强制召回 Skill 的最低阈值
RAG_INTERVENE_TOP_K = 2           # 反思时系统自动检索本地手册的召回数量
RAG_INTERVENE_MIN_SCORE = 0.6     # 反思检索的最低相似度阈值
MAX_REFLECT_COUNT = 5             # 任务内最多允许触发几次阶段反思
MAX_SYS_CHARS = 28000             # Prompt 物理截断上限
MAX_OUTPUT_CHARS = 3000           # 工具单次输出截断上限

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
SIMILARITY_ARGS_THRESHOLD = 0.90
SIMILARITY_OUT_THRESHOLD = 0.95
SIGNATURE_DUP_THRESHOLD = 3
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
ENABLE_PREFERENCE_MEMORY = False
SYSTEM_PROMPT = f"""你是一个智能助手，用中文回答。回答简洁直接。
【系统环境】当前系统：{OS_SYSTEM}，默认 Shell：{EXEC_SHELL}。输出文件保存在 {OUTPUT_DIR}。"""
AGENT_LANG = os.environ.get("AGENT_LANG", "zh")
OCR_LANG = os.environ.get("AGENT_OCR_LANG", "ch")