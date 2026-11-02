import os
import sys
import platform

# ========== 路径（动态推导） ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "agent.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ========== 系统与环境解耦 ==========
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

# ========== 后端选择 ==========
LLM_BACKEND = os.environ.get("AGENT_LLM_BACKEND", "llamacpp_server")
# 路由后端也动态获取，默认跟主后端一致
ROUTER_BACKEND = os.environ.get("AGENT_ROUTER_BACKEND", LLM_BACKEND)

# ========== 云端 API 配置 ==========
CLOUD_API_BASE = os.environ.get("AGENT_API_BASE", "https://api.deepseek.com/v1")
CLOUD_API_KEY = os.environ.get("AGENT_API_KEY", "your-api-key-here")
CLOUD_MODEL_NAME = os.environ.get("AGENT_CLOUD_MODEL", "deepseek-chat")

# ========== Ollama ==========
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TIMEOUT = 600

# ========== Planner (9B GPU) ==========
# 允许通过环境变量覆盖二进制路径和模型路径
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

# ========== Router (1.5B CPU) ==========
ROUTER_SERVER_BIN   = LLAMACPP_BIN
ROUTER_SERVER_MODEL = os.environ.get("ROUTER_SERVER_MODEL", os.path.expanduser("~/models/qwen2.5-1.5b-instruct.gguf"))

ROUTER_SERVER_HOST  = os.environ.get("ROUTER_SERVER_HOST", "127.0.0.1")
ROUTER_SERVER_PORT  = int(os.environ.get("ROUTER_SERVER_PORT", 8082))
ROUTER_SERVER_URL   = f"http://{ROUTER_SERVER_HOST}:{ROUTER_SERVER_PORT}"

ROUTER_SERVER_CTX   = 4096
ROUTER_SERVER_NGL   = 0            # 0 = 纯 CPU
ROUTER_SERVER_PARALLEL = 1
ROUTER_SERVER_TIMEOUT  = 120
ROUTER_SERVER_REASONING = "off"
ROUTER_SERVER_REASONING_BUDGET = 0
ROUTER_SERVER_CHAT_TEMPLATE_KWARGS = '{"enable_thinking": false}'

# ========== 搜索后端 ==========
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080/search")

SEARCH_BACKENDS = ["parallel"]
SEARCH_SOURCE_ALIASES = {
    "parallel": "parallel",
    "searxng": "searxng",
    "web": "parallel",
    "网络": "parallel",
    "本地": "searxng",
    "local": "searxng",
}

# ========== Browser (CDP) ==========
CHROME_BIN = os.environ.get("CHROME_BIN", "")
CHROME_PORT = 9222
CHROME_USER_DATA = "/tmp/chrome-debug"
CHROME_STDOUT_LOG = "/tmp/chromium_stdout.log"
CHROME_STDERR_LOG = "/tmp/chromium_stderr.log"

# ========== Browser (Playwright) ==========
BROWSER_PROFILE_DIR = os.path.join(DATA_DIR, "browser-profile")
BROWSER_HEADLESS = False
BROWSER_TIMEOUT = 15000

# ========== 复杂度分层 ==========
COMPLEXITY_HINTS = ("low", "medium", "high")

# ========== 模型基础参数 ==========
MAX_ATTEMPTS = 50
FAILURE_THRESHOLD = 5
SAME_CALL_THRESHOLD = 3

# ========== 日志轮转开关 ==========
ENABLE_LOG_ROTATION = False

# ========== 模型名称 ==========
ROUTER_MODEL = "qwen2.5:1.5b-instruct"
PLANNER_MODEL = "qwen3.5:9b"

# ========== 记忆与上下文压缩 ==========
HISTORY_LIMIT = 12
COMPRESS_KEEP_RECENT = 8
COMPRESS_MAX_CHARS = 300
HISTORY_RESULT_TRUNCATE = 200
TURN_HISTORY_MAX = 100

# ========== 推理参数 ==========
PLANNER_OPTIONS = {
    "temperature": 0.1,
    "num_predict": 16384,
    "num_ctx": 16384,
    "top_p": 0.9,
    "think": False,
}
ROUTER_OPTIONS = {
    "temperature": 0.0,
    "num_predict": 200,
    "num_ctx": 4096,
    "think": False,
}

# ========== Embedding ==========
EMBED_BACKEND = "llamacpp_direct"
EMBED_MODEL_PATH = os.environ.get("EMBED_MODEL_PATH", os.path.expanduser("~/models/bge-m3-Q8_0.gguf"))
EMBED_DIMENSION = 1024
EMBED_N_GPU_LAYERS = 0
EMBED_N_CTX = 512

# ========== 向量库 ==========
VECTOR_BACKEND = "chromadb"
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
CHROMA_COLLECTION = "memories"

# ========== 记忆检索 ==========
MEMORY_TOP_K = 3
MEMORY_MIN_SCORE = 0.5

# ========== 输出目录 ==========
# 允许通过环境变量覆盖默认桌面路径
OUTPUT_DIR = os.environ.get("AGENT_OUTPUT_DIR", os.path.join(os.path.expanduser("~"), "Desktop"))
SCREENSHOT_DIR = os.environ.get("AGENT_SCREENSHOT_DIR", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))

# ========== 新增：集中管理的魔法数字 ==========
MAX_SYS_CHARS = 28000
MAX_OUTPUT_CHARS = 3000
SHRINK_KEEP_HEAD = 2
SHRINK_KEEP_TAIL = 6
SHRINK_MAX_CHARS = 300
SHRINK_MIN_CHARS = 600
SEARCH_INTERVENE_THRESHOLD = 3
TOOL_FAIL_INTERVENE_THRESHOLD = 3
SIGNATURE_WINDOW_SIZE = 6
SIGNATURE_DUP_THRESHOLD = 3
REFLECT_MAX_LEN = 100
REFLECT_CAUSAL_WORDS = ["因为", "由于", "导致", "从而"]
DIALOGUE_KEYWORDS = ["你好", "谢谢", "你是谁", "怎么回事", "你是不是", "刚才干了啥"]

# ========== 偏好记忆开关 ==========
# False: 禁用 AI 自动生成 preference（防 9B 乱记废话、瞎编习惯）
# True: 允许 AI 记录用户长期偏好
ENABLE_PREFERENCE_MEMORY = False

# ========== 系统提示（加入了动态环境注入） ==========
SYSTEM_PROMPT = f"""你是一个智能助手，用中文回答。回答简洁直接。
【系统环境】当前系统：{OS_SYSTEM}，默认 Shell：{EXEC_SHELL}。输出文件保存在 {OUTPUT_DIR}。"""

# config.py 的末尾加上：
AGENT_LANG = os.environ.get("AGENT_LANG", "zh")  # "zh" 或 "en"