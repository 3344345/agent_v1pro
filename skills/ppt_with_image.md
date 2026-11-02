场景: 生成一个带标题和图片的精美 PPT
说明: 必须使用 execute_python，并引入 python-pptx 库。

代码骨架:
```python
import os
from pptx import Presentation
from pptx.util import Inches

prs = Presentation()
# 添加标题幻灯片
title_slide_layout = prs.slide_layouts[0]
slide = prs.slides.add_slide(title_slide_layout)
slide.shapes.title.text = "Agent V1 Pro 自动化报告"
slide.placeholders[1].text = "由本地大模型生成"

# 添加图文幻灯片
blank_slide_layout = prs.slide_layouts[5]
slide2 = prs.slides.add_slide(blank_slide_layout)
slide2.shapes.title.text = "数据可视化结果"

# 插入图片
img_path = os.path.expanduser("~/Desktop/chart.png")
if os.path.exists(img_path):
    slide2.shapes.add_picture(img_path, Inches(1), Inches(1.5), width=Inches(6))

output_path = os.path.expanduser("~/Desktop/output.pptx")
prs.save(output_path)
print(f"✅ PPT 已保存至: {output_path}")
```