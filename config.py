import os
import sys
import platform

# ==============================================================================
# 基础路径配置
# 动态推导项目根目录，确保跨平台、换机器后代码无需修改。
# 所有缓存、日志、向量数据库都基于此路径生成，避免绝对路径写死。
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "agent.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ==============================================================================
# 操作系统与 Shell 环境解耦
# 自动识别当前系统，注入对应的 Shell 和 matplotlib 中文字体。
# 避免在 Windows 上调用 bash，或在 Mac 上找不到中文字体导致乱码。
# ==============================================================================
OS_SYSTEM = platform.system()
if OS_SYSTEM == "Darwin":         # macOS
    EXEC_SHELL = "/bin/zsh"
    MPL_FONT_FAMILY = "PingFang SC"
elif OS_SYSTEM == "Windows":      # Windows
    EXEC_SHELL = "powershell.exe"
    MPL_FONT_FAMILY = "Microsoft YaHei"
else:                             # Linux (Ubuntu/Arch等)
    EXEC_SHELL = "/bin/bash"
    MPL_FONT_FAMILY = "Noto Sans CJK SC"

# ==============================================================================
# 模型后端选择
# LLM_BACKEND 可选值: "llamacpp_server" (本地), "ollama" (本地), "cloud_api" (云端)
# ROUTER_BACKEND 默认跟随主后端，也可以单独指定（比如主模型用云端，路由用本地极速小模型）
# ==============================================================================
LLM_BACKEND = os.environ.get("AGENT_LLM_BACKEND", "llamacpp_server")
ROUTER_BACKEND = os.environ.get("AGENT_ROUTER_BACKEND", LLM_BACKEND)
PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "qwen3.5:9b")
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "qwen2.5:1.5b-instruct")

# ==============================================================================
# 云端 API 配置
# 默认兼容 OpenAI 格式，目前预设为 DeepSeek。通过环境变量(.env)注入 Key。
# ==============================================================================
CLOUD_API_BASE = os.environ.get("AGENT_API_BASE", "https://api.deepseek.com/v1")
CLOUD_API_KEY = os.environ.get("AGENT_API_KEY", "your-api-key-here")
CLOUD_MODEL_NAME = os.environ.get("AGENT_CLOUD_MODEL", "deepseek-chat")

# ==============================================================================
# Ollama 本地后端配置
# 默认连接本地 11434 端口，如果 Ollama 挂在其他机器上，可通过环境变量覆盖。
# ==============================================================================
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TIMEOUT = 600  # 大模型单次请求超时时间（秒）

# ==============================================================================
# Planner (执行大脑，通常为 9B/7B，跑在 GPU 上)
# 支持通过环境变量覆盖二进制路径和模型路径，方便跨平台部署。
# ==============================================================================
LLAMACPP_BIN   = os.environ.get("LLAMACPP_BIN", os.path.expanduser("~/projects/llama.cpp/build/bin/llama-server"))
LLAMACPP_MODEL = os.environ.get("LLAMACPP_MODEL", os.path.expanduser("~/models/qwen3.5-9b.gguf"))

LLAMACPP_HOST  = os.environ.get("LLAMACPP_HOST", "127.0.0.1")
LLAMACPP_PORT  = int(os.environ.get("LLAMACPP_PORT", 8081))
LLAMACPP_URL   = f"http://{LLAMACPP_HOST}:{LLAMACPP_PORT}"

LLAMACPP_CTX   = 16384    # 上下文窗口大小 (Token)
LLAMACPP_NGL   = 99       # 卸载到 GPU 的层数，99 表示全部卸载
LLAMACPP_PARALLEL = 1     # 并行处理请求数
LLAMACPP_TIMEOUT = 600    # llama-server 内部超时时间
LLAMACPP_KV_QUANT = False # 👈 补上了这里，控制是否开启 KV 缓存量化

# 关闭思考模式（针对 Qwen3 等自带思维链的模型，关闭后可加速并减少幻觉）
LLAMACPP_REASONING = "off"
LLAMACPP_REASONING_BUDGET = 0
LLAMACPP_CHAT_TEMPLATE_KWARGS = '{"enable_thinking": false}'

# ==============================================================================
# Router (路由翻译官，通常为 1.5B，纯 CPU 跑以节省显存)
# 负责极速分析用户意图、提取关键词，并判断任务复杂度。
# ==============================================================================
ROUTER_SERVER_BIN   = LLAMACPP_BIN
ROUTER_SERVER_MODEL = os.environ.get("ROUTER_SERVER_MODEL", os.path.expanduser("~/models/qwen2.5-1.5b-instruct.gguf"))

ROUTER_SERVER_HOST  = os.environ.get("ROUTER_SERVER_HOST", "127.0.0.1")
ROUTER_SERVER_PORT  = int(os.environ.get("ROUTER_SERVER_PORT", 8082))
ROUTER_SERVER_URL   = f"http://{ROUTER_SERVER_HOST}:{ROUTER_SERVER_PORT}"

ROUTER_SERVER_CTX   = 4096    # 路由模型不需要长上下文
ROUTER_SERVER_NGL   = 0       # 0 = 纯 CPU
ROUTER_SERVER_PARALLEL = 1
ROUTER_SERVER_TIMEOUT  = 120
ROUTER_SERVER_REASONING = "off"
ROUTER_SERVER_REASONING_BUDGET = 0
ROUTER_SERVER_CHAT_TEMPLATE_KWARGS = '{"enable_thinking": false}'

# ==============================================================================
# 网络搜索配置
# 默认使用 parallel (并行搜索) 和 searxng (本地聚合搜索)
# ==============================================================================
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080/search")
SEARCH_BACKENDS = ["parallel"]
SEARCH_SOURCE_ALIASES = {
    "parallel": "parallel", "searxng": "searxng",
    "web": "parallel", "网络": "parallel",
    "本地": "searxng", "local": "searxng",
}

# ==============================================================================
# 浏览器与自动化配置 (Playwright)
# 使用持久化上下文保存 Cookie，避免每次打开网页都要重新登录。
# ==============================================================================
CHROME_BIN = os.environ.get("CHROME_BIN", "")
CHROME_PORT = 9222
CHROME_USER_DATA = "/tmp/chrome-debug"
CHROME_STDOUT_LOG = "/tmp/chromium_stdout.log"
CHROME_STDERR_LOG = "/tmp/chromium_stderr.log"

BROWSER_PROFILE_DIR = os.path.join(DATA_DIR, "browser-profile")  # 浏览器用户数据保存目录
BROWSER_HEADLESS = False       # 是否无头模式。False 表示你可以看到浏览器弹出来操作
BROWSER_TIMEOUT = 15000        # Playwright 找元素或加载页面的默认超时时间（毫秒）

# ==============================================================================
# 复杂度分层
# 供 Router 模型输出使用的固定枚举值。
# ==============================================================================
COMPLEXITY_HINTS = ("low", "medium", "high")

# ==============================================================================
# 核心防暴走与熔断机制配置
# 这些是系统的“刹车片”和“防呆设计”，极其重要！
# ==============================================================================
MAX_ATTEMPTS = 50              # 单次任务最大循环轮数（防止无限转圈）
FAILURE_THRESHOLD = 5          # 连续失败 N 次直接彻底终止任务
SAME_CALL_THRESHOLD = 3        # 工具连续执行完全相同参数的次数上限

# ==============================================================================
# 日志轮转配置
# 开发环境建议 False（方便查历史），生产环境建议 True（防止日志撑爆硬盘）
# ==============================================================================
ENABLE_LOG_ROTATION = False

# ==============================================================================
# 推理模型默认标识
# 用于写入日志、或者在 Ollama 模式下查找对应模型。
# ==============================================================================
ROUTER_MODEL = "qwen2.5:1.5b-instruct"
PLANNER_MODEL = "qwen3.5:9b"

# ==============================================================================
# 上下文压缩与历史记录管理
# 防止 Agent 聊了几十轮后，上下文（Token）直接撑爆。
# ==============================================================================
HISTORY_LIMIT = 12             # 未压缩轮次达到 N 轮时，触发后台压缩
COMPRESS_KEEP_RECENT = 8       # 压缩后保留最近 N 轮的完整对话
COMPRESS_MAX_CHARS = 300       # 压缩生成的摘要最大字符数
HISTORY_RESULT_TRUNCATE = 200  # 写入历史库时，单次工具结果的最大截断长度
TURN_HISTORY_MAX = 100         # 本地 DB 保留的历史记录最大条数

# ==============================================================================
# LLM 推理参数
# ==============================================================================
PLANNER_OPTIONS = {
    "temperature": 0.1,        # 执行器温度低一点，保证逻辑严谨
    "num_predict": 16384,
    "num_ctx": 16384,
    "top_p": 0.9,
    "think": False,
}
ROUTER_OPTIONS = {
    "temperature": 0.0,        # 路由器温度设为 0，保证输出的 JSON 格式绝对稳定
    "num_predict": 200,        # 路由不需要长篇大论
    "num_ctx": 4096,
    "think": False,
}

# ==============================================================================
# Embedding (向量化) 配置
# 默认使用 llamacpp_direct 纯 CPU 跑，也可以切云端或 fastembed
# ==============================================================================
EMBED_BACKEND = os.environ.get("EMBED_BACKEND", "llamacpp_direct") # 可选：ollama, fastembed, llamacpp_direct
EMBED_MODEL_PATH = os.environ.get("EMBED_MODEL_PATH", os.path.expanduser("~/models/bge-m3-Q8_0.gguf"))
EMBED_DIMENSION = 1024            # bge-m3 产生的向量维度（注意：fastembed 是 512，切换必清库）
EMBED_N_GPU_LAYERS = 0            # 0 = 纯 CPU
EMBED_N_CTX = 512

# ==============================================================================
# 向量数据库配置
# ==============================================================================
VECTOR_BACKEND = "chromadb"
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
CHROMA_COLLECTION = "memories"

# ==============================================================================
# 记忆检索参数
# ==============================================================================
MEMORY_TOP_K = 3               # 每次检索最相关的 3 条记忆
MEMORY_MIN_SCORE = 0.5         # 相似度低于 0.5 的直接丢弃（防止答非所问）

# ==============================================================================
# 输出文件与截图目录
# 强制 Agent 将生成的文件保存在这里，避免乱丢。可通过环境变量覆盖。
# ==============================================================================
OUTPUT_DIR = os.environ.get("AGENT_OUTPUT_DIR", os.path.join(os.path.expanduser("~"), "Desktop"))
SCREENSHOT_DIR = os.environ.get("AGENT_SCREENSHOT_DIR", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))

# ==============================================================================
# 🚨 高阶防暴走与死循环熔断魔法数字 (极其重要，请勿乱动)
# ==============================================================================
SIMILARITY_WINDOW_SIZE = 5        # 相似度观察滑动窗口（最近 N 次调用）
SIMILARITY_ARGS_THRESHOLD = 0.90  # 参数相似度阈值（大于 0.9 判定为微调参数刷屏）
SIMILARITY_OUT_THRESHOLD = 0.95   # 结果相似度阈值（大于 0.95 判定为无进展/死循环）
HISTORY_INVALID_MINUTES = 15      # 历史状态失效时间阈值（分钟，超过则提醒模型环境可能变了）
HISTORY_INJECT_LIMIT = 3          # 注入 Prompt 上下文的最近历史轮数
MAX_SYS_CHARS = 28000             # Prompt 物理截断上限（超了直接腰斩中间部分）
MAX_OUTPUT_CHARS = 3000           # 工具单次输出截断上限
SHRINK_KEEP_HEAD = 2              # 轮内压缩时：保留头几条消息
SHRINK_KEEP_TAIL = 6              # 轮内压缩时：保留尾几条消息
SHRINK_MAX_CHARS = 300            # 中间老旧 tool 消息压缩至多少字
SHRINK_MIN_CHARS = 600            # 低于 600 字的不压，免得增加噪音
SEARCH_INTERVENE_THRESHOLD = 3    # 连续搜索 N 次强制干预，逼迫模型给结论
TOOL_FAIL_INTERVENE_THRESHOLD = 3 # 工具连续失败 N 次触发阶段性反思
SIGNATURE_WINDOW_SIZE = 6         # 死循环签名检测的滑动窗口大小
SIGNATURE_DUP_THRESHOLD = 3       # 窗口内同签名出现 N 次直接熔断
REFLECT_MAX_LEN = 100             # 反思写入记忆的字数上限
REFLECT_CAUSAL_WORDS = ["因为", "由于", "导致", "从而"]  # 反思拦截词（防甩锅）
DIALOGUE_KEYWORDS = ["你好", "谢谢", "你是谁", "怎么回事", "你是不是", "刚才干了啥"] # 强制降级为闲聊的关键词

# ==============================================================================
# 偏好记忆开关
# False: 禁用 AI 自动生成 preference（防小模型乱记废话、瞎编习惯）
# True: 允许 AI 记录用户长期偏好（建议换大模型后再打开）
# ==============================================================================
ENABLE_PREFERENCE_MEMORY = False

# ==============================================================================
# 基础系统提示 (在 prompts.py 中会与更复杂的规则合并)
# ==============================================================================
SYSTEM_PROMPT = f"""你是一个智能助手，用中文回答。回答简洁直接。
【系统环境】当前系统：{OS_SYSTEM}，默认 Shell：{EXEC_SHELL}。输出文件保存在 {OUTPUT_DIR}。"""

# ==============================================================================
# 多语言与 OCR 配置
# ==============================================================================
AGENT_LANG = os.environ.get("AGENT_LANG", "zh")  # Agent 回答语言: "zh" 或 "en"
# 'ch' 天然支持中英文混排（推荐）；'en' 为纯英文（速度略快）
OCR_LANG = os.environ.get("AGENT_OCR_LANG", "ch")