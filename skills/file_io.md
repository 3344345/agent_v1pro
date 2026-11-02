场景: 读写本地文本文件
说明: 系统没有提供专用的读写工具，必须通过 execute_python 完成。请严格遵守以下模板，防止文件不存在、编码错误或截断上下文。

步骤:
1. 读取文件（防爆截断）：
```python
import os
path = os.path.expanduser("~/Desktop/example.txt")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        # 最多只读 3000 个字符，防止撑爆上下文
        content = f.read(3000)
        print(content)
        print(f"\n[已读取 {len(content)} 字符]")
else:
    print("文件不存在")
```

2. 写入文件（自动建目录）：
```python
import os
path = os.path.expanduser("~/Desktop/output/result.md")
# 自动创建父目录
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    f.write("要写入的内容")
print(f"写入成功: {path}")
```

验证: 
- 读取前必须先 `os.path.exists`。
- 读取时必须限制字符数。
- 写入时必须带上 `encoding="utf-8"`，且先建目录。