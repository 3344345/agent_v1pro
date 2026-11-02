import json
import os

from config import DATA_DIR

EXAMPLES_FILE = os.path.join(DATA_DIR, "intents.json")


DEFAULT_EXAMPLES = {
    "examples": [
        {"input": "你好", "summary": "用户在打招呼", "keywords": [], "hint": "low"},
        {"input": "看一下桌面有哪些文件", "summary": "用户想列出桌面上的文件",
         "keywords": ["桌面", "文件"], "hint": "low"},
        {"input": "搜一下 Python 3.12 新特性", "summary": "用户想通过网络搜索了解 Python 3.12 的新特性",
         "keywords": ["Python 3.12", "新特性"], "hint": "low"},
    ]
}


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_examples() -> list:
    _ensure_data_dir()
    if not os.path.exists(EXAMPLES_FILE):
        save_examples(DEFAULT_EXAMPLES)
        return list(DEFAULT_EXAMPLES["examples"])
    try:
        with open(EXAMPLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("examples", [])
    except Exception as e:
        print(f"[intent_registry] 加载失败: {e}")
        return list(DEFAULT_EXAMPLES["examples"])


def save_examples(data: dict) -> bool:
    _ensure_data_dir()
    try:
        with open(EXAMPLES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[intent_registry] 保存失败: {e}")
        return False


# ========== 缓存 ==========
_cache = None


def get_examples(reload: bool = False) -> list:
    global _cache
    if _cache is None or reload:
        _cache = load_examples()
    return _cache


def reload_cache():
    global _cache
    _cache = load_examples()


# ========== 自学习接口 ==========
def add_example(input_text: str, summary: str,
                keywords: list = None, hint: str = "low") -> tuple:
    if not input_text or not summary:
        return False, "input 和 summary 不能为空"
    if hint not in ("low", "medium", "high"):
        hint = "low"

    examples = load_examples()
    examples.append({
        "input": input_text,
        "summary": summary,
        "keywords": keywords or [],
        "hint": hint,
    })
    if save_examples({"examples": examples}):
        reload_cache()
        return True, "ok"
    return False, "保存失败"