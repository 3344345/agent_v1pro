#!/usr/bin/env python3
"""记忆库管理工具。所有操作走 store 接口，保证 SQLite 与 Chroma 一致。"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.memory import get_store  # noqa: E402


def cmd_list(args):
    store = get_store()
    cats = [args.category] if args.category else None
    items = store.list_all(categories=cats, limit=args.limit)
    for it in items:
        preview = (it["content"] or "").replace("\n", " ")[:80]
        print(f"[{it['id']:>4}] [{it['category']:<11}] {preview}")
    print(f"\n共 {len(items)} 条")


def cmd_show(args):
    store = get_store()
    item = store.get(args.id)
    if not item:
        print(f"id={args.id} 不存在或已删除")
        return
    for k in ("id", "category", "scope", "source", "trigger",
              "created_at", "last_used_at", "hit_count"):
        print(f"{k:<13}: {item.get(k)}")
    print("content:")
    print(item["content"])


def cmd_search(args):
    store = get_store()
    hits = store.search(
        query=args.query,
        categories=[args.category] if args.category else None,
        top_k=args.top_k,
        min_score=0.0,
    )
    for h in hits:
        preview = (h["content"] or "").replace("\n", " ")[:80]
        print(f"[{h['score']:.3f}] [{h['id']:>4}] [{h['category']:<11}] {preview}")


def cmd_delete(args):
    store = get_store()
    for mid in args.ids:
        ok = store.delete(mid)
        print(f"delete {mid}: {'✅' if ok else '❌ 不存在'}")


def cmd_import(args):
    store = get_store()
    src = Path(args.path)
    if not src.exists():
        print(f"路径不存在：{src}")
        return
    files = sorted(src.glob("*.md")) if src.is_dir() else [src]
    if not files:
        print(f"没有找到 .md 文件：{args.path}")
        return

    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            print(f"skip {f.name}: 空文件")
            continue
        existing = store.search(
            query=content, categories=["skill"], top_k=1, min_score=0.92
        )
        if existing:
            print(f"skip {f.name}: 相似度 {existing[0]['score']:.2f} "
                  f"已存在（id={existing[0]['id']}）")
            continue
        mid = store.save(
            category="skill",
            content=content,
            source=f"file:{f.name}",
        )
        print(f"imported {f.name} -> id={mid}")


def main():
    p = argparse.ArgumentParser(description="Agent 记忆库管理")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="列出记忆")
    s.add_argument("--category", default=None)
    s.add_argument("--limit", type=int, default=100)
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="查看单条")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("search", help="语义搜索")
    s.add_argument("query")
    s.add_argument("--category", default=None)
    s.add_argument("--top-k", type=int, default=5)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("delete", help="删除（SQLite + Chroma 一起删）")
    s.add_argument("ids", type=int, nargs="+")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("import", help="导入 skill 文件或目录")
    s.add_argument("path")
    s.set_defaults(func=cmd_import)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()