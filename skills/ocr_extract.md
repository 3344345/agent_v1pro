场景: 从本地图片或纯图 PDF 中提取文字（OCR）
说明: 必须使用 `execute_python` 工具，绝对禁止使用 `execute_command` 拼 heredoc！PaddleOCR 版本更新，必须使用以下兼容代码。

步骤:
1. 如果输入是 PDF（纯图 PDF），先使用 `pymupdf` 把目标页渲染成 PNG 图片，保存在桌面。
2. 然后使用 `execute_python` 执行以下完整代码，将 `img_path` 替换为你刚才生成的图片路径：

```python
import os
from paddleocr import PaddleOCR
import traceback

img_path = os.path.expanduser("~/Desktop/target_page.png")

if not os.path.exists(img_path):
    print(f"❌ 文件不存在: {img_path}")
else:
    try:
        # 关键：最新版 PaddleOCR 的正确初始化方式
        # 不要用 show_log，不要用 use_angle_cls
        ocr = PaddleOCR(lang='ch')
        
        # 执行 OCR
        result = ocr.ocr(img_path)
        
        if not result or not result[0]:
            print("⚠️ 未识别到任何文字")
        else:
            print("✅ 提取成功，内容如下：")
            for line in result[0]:
                text = line[1][0]
                print(text)
    except Exception as e:
        print(f"❌ OCR 执行失败: {e}")
        traceback.print_exc()
```

3. 如果需要处理 PDF 第一页，渲染代码如下：
```python
import fitz
doc = fitz.open("你的PDF绝对路径.pdf")
page = doc[0]
pix = page.get_pixmap(dpi=200)
img_path = "~/Desktop/target_page.png"
pix.save(img_path)
print(f"✅ PDF 第一页已转为图片: {img_path}")
```

验证: 
- 必须在 execute_python 中看到完整的文字输出（而不是只有 warning）。
- 如果报错，仔细看报错信息，不要重复盲目试错。
