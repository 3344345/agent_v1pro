场景: 生成一个带文本和图片的 Word 文档
说明: 必须使用 execute_python，并引入 python-docx 库。

代码骨架:
```python
import os
from docx import Document
from docx.shared import Inches

doc = Document()
doc.add_heading('这里是标题', 0)
doc.add_paragraph('这里是正文段落。')

# 插入图片（注意图片路径必须存在）
if os.path.exists("你的图片路径.png"):
    doc.add_picture("你的图片路径.png", width=Inches(5.0))

output_path = os.path.expanduser("~/Desktop/output.docx")
doc.save(output_path)
print(f"✅ 文档已保存至: {output_path}")
```