import os
import tempfile
from registries.tool_registry import register
from core import browser
from logger import log_event
from config import OCR_LANG

_ocr_engine = None

def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=False, lang=OCR_LANG, show_log=False)
        except ImportError:
            raise RuntimeError("未安装 PaddleOCR。请运行: pip install paddlepaddle paddleocr pillow")
        except Exception as e:
            raise RuntimeError(f"PaddleOCR 初始化失败: {e}")
    return _ocr_engine

@register(
    name="browser_ocr_extract",
    description="【视觉兜底】对当前网页截图并提取可见文本（支持中英混排）。仅在原生 snapshot 拿不到文本时使用。",
    parameters={"type": "object", "properties": {}},
    requires_network=False,
)
def browser_ocr_extract() -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        
        res = browser.screenshot(temp_path)
        if "❌" in res:
            return res
            
        ocr = _get_ocr()
        result = ocr.ocr(temp_path, cls=False)
        os.remove(temp_path)
        
        if not result or not result[0]:
            return "⚠️ OCR 未在当前页面识别到任何文字。"
            
        texts = [line[1][0] for line in result[0] if line[1][1] > 0.6]
        return "✅ OCR 提取结果:\n" + "\n".join(texts)
        
    except Exception as e:
        return f"❌ OCR 提取失败: {e}"

@register(
    name="browser_ocr_click",
    description=(
        "【视觉兜底】使用 OCR 视觉识别寻找页面上的文字，并模拟物理鼠标点击其中心位置。\n"
        "适用场景：原生 browser_click 找不到元素，或按钮是纯图片无法定位。\n"
        "传入你想点击的【纯文本】即可。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "target_text": {"type": "string", "description": "要点击的文字，如 '登录'"},
            "exact_match": {"type": "boolean", "description": "是否精确匹配"}
        },
        "required": ["target_text"]
    },
    requires_network=False,
)
def browser_ocr_click(target_text: str, exact_match: bool = False) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
            
        res = browser.screenshot(temp_path)
        if "❌" in res:
            return res
            
        ocr = _get_ocr()
        result = ocr.ocr(temp_path, cls=False)
        os.remove(temp_path)
        
        if not result or not result[0]:
            return f"❌ OCR 未在页面上找到任何文字。"
            
        target_box = None
        matched_text = ""
        
        for line in result[0]:
            box = line[0]
            text = line[1][0]
            score = line[1][1]
            
            if score < 0.6: continue
            
            is_match = (target_text == text) if exact_match else (target_text in text)
            if is_match:
                x_coords = [pt[0] for pt in box]
                y_coords = [pt[1] for pt in box]
                target_box = (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
                matched_text = text
                break
                
        if not target_box:
            return f"❌ OCR 找不到文字 '{target_text}'。"
            
        # 调用刚写的带光标动画的视觉点击
        from .interaction import browser_visual_click
        click_res = browser_visual_click(target_box[0], target_box[1])
        
        log_event("info", f"OCR 成功点击: '{matched_text}'", extra={"x": target_box[0], "y": target_box[1]})
        return f"✅ 成功通过 OCR 找到 '{matched_text}' 并点击。\n{click_res}"
        
    except Exception as e:
        return f"❌ OCR 点击失败: {e}"