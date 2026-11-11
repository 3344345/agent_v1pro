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
            # 🚨 修复 PaddleOCR 3.x 的最新报错，移除 cls 参数相关配置
            _ocr_engine = PaddleOCR(use_angle_cls=False, lang=OCR_LANG)
        except ImportError:
            raise RuntimeError("未安装 PaddleOCR。请运行: pip install paddlepaddle paddleocr pillow")
        except Exception as e:
            raise RuntimeError(f"PaddleOCR 初始化失败: {e}")
    return _ocr_engine

@register(
    name="browser_ocr_extract",
    description="【视觉兜底】对当前网页截图并提取可见文本。",
    parameters={"type": "object", "properties": {}},
    requires_network=False,
)
def browser_ocr_extract() -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        res = browser.screenshot(temp_path)
        if "❌" in res: return res
        ocr = _get_ocr()
        # 🚨 修复：最新版用 predict，或直接 ocr(temp_path) 不传 cls
        result = ocr.predict(temp_path) if hasattr(ocr, 'predict') else ocr.ocr(temp_path)
        os.remove(temp_path)
        
        if not result or not result[0]: return "⚠️ OCR 未识别到文字。"
        
        lines = []
        # 兼容不同版本的返回结构
        res_data = result[0].get("rec_texts", []) if isinstance(result[0], dict) else [line[1][0] for line in result[0]]
        for text in res_data:
            lines.append(f"- {text}")
        return "✅ OCR 提取结果:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ OCR 提取失败: {e}"

@register(
    name="browser_ocr_click",
    description="【视觉兜底】使用 OCR 视觉识别寻找页面上的文字并物理点击。",
    parameters={
        "type": "object",
        "properties": {
            "target_text": {"type": "string", "description": "要点击的文字"},
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
        if "❌" in res: return res
        
        ocr = _get_ocr()
        # 🚨 修复：移除 cls=False 参数
        result = ocr.predict(temp_path) if hasattr(ocr, 'predict') else ocr.ocr(temp_path)
        os.remove(temp_path)
        
        if not result or not result[0]: return f"❌ OCR 未在页面上找到任何文字。"
        
        target_box = None
        matched_text = ""
        
        # 兼容新版和旧版的返回结构
        if isinstance(result[0], dict) and "rec_boxes" in result[0]:
            texts = result[0]["rec_texts"]
            boxes = result[0]["rec_boxes"]
            scores = result[0].get("rec_scores", [1.0]*len(texts))
            iter_data = zip(texts, boxes, scores)
        else:
            iter_data = [(line[1][0], line[0], line[1][1]) for line in result[0]]

        for text, box, score in iter_data:
            if score < 0.6: continue
            is_match = (target_text == text) if exact_match else (target_text in text)
            if is_match:
                # 兼容多边形框
                x_coords = [pt[0] for pt in box] if isinstance(box, list) and isinstance(box[0], list) else [box[0], box[2]]
                y_coords = [pt[1] for pt in box] if isinstance(box, list) and isinstance(box[0], list) else [box[1], box[3]]
                target_box = (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
                matched_text = text
                break
                
        if not target_box: return f"❌ OCR 找不到文字 '{target_text}'。"
        
        from .interaction import browser_visual_click
        click_res = browser_visual_click(target_box[0], target_box[1])
        return f"✅ 成功通过 OCR 找到 '{matched_text}' 并点击。\n{click_res}"
    except Exception as e:
        return f"❌ OCR 点击失败: {e}"