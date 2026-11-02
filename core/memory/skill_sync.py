import os
import hashlib
from pathlib import Path
from logger import log_event
from core.memory import get_store

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
HASH_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".skills_hash"

def _calc_dir_hash():
    """计算 skills 目录下所有 md 文件的综合 Hash"""
    if not SKILLS_DIR.exists():
        return ""
    hash_md5 = hashlib.md5()
    for filepath in sorted(SKILLS_DIR.glob("*.md")):
        hash_md5.update(filepath.name.encode("utf-8"))
        hash_md5.update(filepath.read_bytes())
    return hash_md5.hexdigest()

def sync_skills():
    """对比 Hash，如果有变动则自动导入 Skill 库"""
    if not SKILLS_DIR.exists():
        return
        
    current_hash = _calc_dir_hash()
    old_hash = ""
    if HASH_FILE.exists():
        old_hash = HASH_FILE.read_text(encoding="utf-8").strip()

    if current_hash == old_hash:
        return  # 没有变化，直接跳过

    log_event("info", "检测到 skills 目录变动，开始自动同步...", stage="memory")
    store = get_store()
    imported_count = 0

    for filepath in SKILLS_DIR.glob("*.md"):
        content = filepath.read_text(encoding="utf-8").strip()
        if not content:
            continue
            
        # 简单的查重：搜索一下有没有极其相似的 skill
        existing = store.search(query=content, categories=["skill"], top_k=1, min_score=0.95)
        if existing:
            continue
            
        # 写入
        store.save(
            category="skill",
            content=content,
            source=f"file:{filepath.name}"
        )
        imported_count += 1

    # 保存新的 Hash
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(current_hash, encoding="utf-8")
    
    if imported_count > 0:
        print(f"📚 自动同步完成：新增了 {imported_count} 条 Skill。")
        log_event("info", f"Skill 自动同步完成，新增 {imported_count} 条", stage="memory")