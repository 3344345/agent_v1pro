"""
core/vision.py — 多模态图像输入的唯一入口

职责：
  1. 能力判定：当前后端 + 当前模型到底能不能看图（不可看则自动降级为纯文本，并告知模型）
  2. 图像预处理：体积/像素校验 → 等比缩放 → JPEG 压缩 → base64 data URL
  3. 组装 OpenAI 标准多模态 content：[{"type":"text"},{"type":"image_url"}]
  4. token 估算：给上下文预算用，避免图片把窗口撑爆

所有阈值、开关、能力表都在 config.py 里，本文件不写死任何数字。
"""
from __future__ import annotations

import base64
import io
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from config import (
    IMAGE_DETAIL,
    IMAGE_EST_TOKENS_PER_IMAGE,
    IMAGE_INPUT_ENABLED,
    IMAGE_INPUT_MODE,
    IMAGE_JPEG_QUALITY,
    IMAGE_MAX_BYTES,
    IMAGE_MAX_COUNT,
    IMAGE_MAX_SIDE,
    IMAGE_FALLBACK_NOTICE,
    LLM_BACKEND,
    SMALL_MODEL_IMAGE_MAX_COUNT,
    SMALL_MODEL_IMAGE_TOKEN_BUDGET,
    SMALL_MODEL_MAX_SIDE,
    SMALL_MODEL_PARAM_B,
    VISION_BACKEND_SUPPORT,
    VISION_FORCE,
    VISION_MODEL_KEYWORDS,
)
from logger import log_event

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:                                     # pragma: no cover
    Image = None
    _HAS_PIL = False


# ------------------------------------------------------------------ 能力判定
def current_model_name(backend: Optional[str] = None) -> str:
    """取当前后端实际用的模型名（claude/9b 之类都在这里区分）。"""
    b = (backend or LLM_BACKEND or "").lower()
    try:
        if b == "cloud_api":
            from config import CLOUD_MODEL_NAME
            return str(CLOUD_MODEL_NAME or "")
        if b == "ollama":
            from config import OLLAMA_MODEL
            return str(OLLAMA_MODEL or "")
        if b in ("llamacpp_server", "llamacpp_direct"):
            from config import LLAMACPP_MODEL
            return str(LLAMACPP_MODEL or "")
    except Exception:
        pass
    return ""


def model_param_b(model_name: str) -> Optional[float]:
    """从模型名里猜参数量(B)：'qwen3.5-9b' -> 9.0，'7B' -> 7.0，猜不出返回 None。"""
    if not model_name:
        return None
    m = re.findall(r"(\d+(?:\.\d+)?)\s*[bB](?![a-zA-Z0-9])", model_name)
    if not m:
        return None
    try:
        return min(float(x) for x in m if float(x) >= 0.5)
    except Exception:
        return None


def is_small_model(model_name: Optional[str] = None) -> bool:
    """9B 这种小模型：上下文紧、视觉编码慢，要走收紧策略。"""
    name = model_name if model_name is not None else current_model_name()
    p = model_param_b(name or "")
    return bool(p is not None and p <= SMALL_MODEL_PARAM_B)


def vision_supported(backend: Optional[str] = None,
                     model: Optional[str] = None) -> Tuple[bool, str]:
    """返回 (能不能看图, 原因)。不能看时调用方应自动降级为纯文本。"""
    if not IMAGE_INPUT_ENABLED:
        return False, "config.IMAGE_INPUT_ENABLED = False（全局关闭了图像输入）"

    b = (backend or LLM_BACKEND or "").lower()
    if not VISION_BACKEND_SUPPORT.get(b, False):
        return False, f"后端 {b} 不支持图像输入（config.VISION_BACKEND_SUPPORT）"

    if VISION_FORCE:
        return True, "VISION_FORCE=True 强制开启"

    name = (model if model is not None else current_model_name(b)) or ""
    low = name.lower()
    if any(k.lower() in low for k in VISION_MODEL_KEYWORDS):
        return True, f"模型 {name} 命中视觉关键字"

    if b == "llamacpp_server":
        return False, (f"本地模型 {name or '(未知)'} 未命中视觉关键字 —— "
                       "需要视觉模型 + 启动时加 --mmproj；确认有视觉能力可设 config.VISION_FORCE = True")

    return False, f"模型 {name or '(未知)'} 未命中 config.VISION_MODEL_KEYWORDS"


def limits(backend: Optional[str] = None) -> Dict[str, Any]:
    """按当前后端/模型算出实际生效的限制（9B 自动收紧）。"""
    small = is_small_model(current_model_name(backend))
    return {
        "small_model": small,
        "max_count": SMALL_MODEL_IMAGE_MAX_COUNT if small else IMAGE_MAX_COUNT,
        "max_side": SMALL_MODEL_MAX_SIDE if small else IMAGE_MAX_SIDE,
        "token_budget": SMALL_MODEL_IMAGE_TOKEN_BUDGET if small else None,
    }


# ------------------------------------------------------------------ 图像预处理
def _to_bytes_from_data_url(data: str) -> Tuple[bytes, str]:
    if data.startswith("data:"):
        head, _, b64 = data.partition(",")
        mime = head[5:].split(";")[0] or "image/png"
        return base64.b64decode(b64), mime
    return base64.b64decode(data), "image/png"


def _normalize(raw: Any) -> Tuple[Optional[bytes], str, str]:
    """把各种前端传法归一成 (原始字节 | None, mime, 外链url)。"""
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("http://") or s.startswith("https://"):
            return None, "", s
        if s.startswith("data:"):
            b, mime = _to_bytes_from_data_url(s)
            return b, mime, ""
        # 本地文件路径：优先按真实文件读取（支持 ~ 展开与相对路径）
        cand = os.path.expanduser(s)
        if os.path.isfile(cand):
            with open(cand, "rb") as f:
                return f.read(), (mimetypes.guess_type(cand)[0] or "image/png"), ""
        # 纯 base64 字符串（无 data: 前缀）
        if len(s) > 200:
            b, mime = _to_bytes_from_data_url(s)
            return b, mime, ""
        return None, "", s

    if isinstance(raw, dict):
        url = raw.get("url") or ""
        if url:
            return None, "", str(url)
        data = raw.get("data") or raw.get("base64") or ""
        if data:
            b, mime = _to_bytes_from_data_url(str(data))
            return b, str(raw.get("mime") or mime), ""
        path = raw.get("path") or ""
        if path and os.path.isfile(path):
            with open(path, "rb") as f:
                return f.read(), raw.get("mime") or (mimetypes.guess_type(path)[0] or "image/png"), ""
    return None, "", ""


def _shrink(data: bytes, mime: str, max_side: int) -> Tuple[bytes, str, int, int]:
    """等比压到长边 <= max_side，统一转 JPEG（带透明度的先铺白底）。"""
    if not _HAS_PIL:
        return data, mime, 0, 0
    try:
        im = Image.open(io.BytesIO(data))
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
        if max(im.size) > max_side:
            im.thumbnail((max_side, max_side), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=IMAGE_JPEG_QUALITY, optimize=True)
        return out.getvalue(), "image/jpeg", im.size[0], im.size[1]
    except Exception as e:
        log_event("warning", f"图像压缩失败，按原图发送: {e}", stage="vision")
        return data, mime, 0, 0


def prepare_images(raw_images: Any,
                   backend: Optional[str] = None,
                   model: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    返回 (image_blocks, warnings, degrade_reason)
      image_blocks : [{"type":"image_url","image_url":{"url":..., "detail":...}}]
      degrade_reason: 非空表示"用户发了图但模型看不到"，调用方要往文本里加提示
    """
    warnings: List[str] = []
    if not raw_images:
        return [], warnings, ""
    if isinstance(raw_images, (str, dict)):
        raw_images = [raw_images]
    if not isinstance(raw_images, list):
        return [], ["图像参数格式不对，已忽略"], ""

    ok, reason = vision_supported(backend, model)
    if not ok:
        n = len(raw_images)
        msg = f"用户随消息附带了 {n} 张图片，但当前模型不支持图像输入（{reason}），你无法看到图片内容。"
        log_event("warning", f"图像已降级为纯文本: {reason}", stage="vision")
        return [], [f"当前模型看不了图：{reason}"], (msg if IMAGE_FALLBACK_NOTICE else "")

    lim = limits(backend)
    if len(raw_images) > lim["max_count"]:
        warnings.append(f"图片数量超限（{len(raw_images)} > {lim['max_count']}），只保留前 {lim['max_count']} 张")
        raw_images = raw_images[: lim["max_count"]]

    blocks: List[Dict[str, Any]] = []
    total_bytes = 0
    for i, raw in enumerate(raw_images, 1):
        try:
            data, mime, url = _normalize(raw)
            if url:
                if IMAGE_INPUT_MODE == "base64":
                    warnings.append(f"第 {i} 张是外链，当前 IMAGE_INPUT_MODE=base64 无法内联，已忽略")
                    continue
                blocks.append({"type": "image_url",
                               "image_url": {"url": url, "detail": IMAGE_DETAIL}})
                continue

            if not data:
                warnings.append(f"第 {i} 张图数据为空，已跳过")
                continue
            if len(data) > IMAGE_MAX_BYTES:
                warnings.append(f"第 {i} 张原始体积 {len(data)/1048576:.1f}MB 超过上限，已尝试压缩")

            out, mime, w, h = _shrink(data, mime, lim["max_side"])
            if len(out) > IMAGE_MAX_BYTES:
                warnings.append(f"第 {i} 张压缩后仍超上限 {IMAGE_MAX_BYTES/1048576:.0f}MB，已丢弃")
                continue
            total_bytes += len(out)
            b64 = base64.b64encode(out).decode("ascii")
            blocks.append({"type": "image_url",
                           "image_url": {"url": f"data:{mime};base64,{b64}", "detail": IMAGE_DETAIL}})
            log_event("debug",
                      f"图像#{i} 已处理 {w}x{h} {len(out)/1024:.0f}KB (small_model={lim['small_model']})",
                      stage="vision")
        except Exception as e:
            warnings.append(f"第 {i} 张图处理失败: {e}")

    if blocks:
        log_event("info", f"已附加 {len(blocks)} 张图片 / {total_bytes/1024:.0f}KB", stage="vision")
    return blocks, warnings, ""


# ------------------------------------------------------------------ content 组装
def build_user_content(text: str, blocks: List[Dict[str, Any]], notice: str = "") -> Any:
    """有图 -> 标准 OpenAI content 数组；无图 -> 纯字符串（零改动兼容旧逻辑）。"""
    pure = text or ""
    if notice:
        pure = f"{pure}\n\n[系统提示] {notice}"
    if not blocks:
        return pure
    return [{"type": "text", "text": pure}] + blocks


def flatten_content(content: Any) -> str:
    """把 content 数组拍平回字符串（日志/记忆/纯文本后端用）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    out.append(part.get("text") or "")
                elif part.get("type") == "image_url":
                    out.append("[图片]")
            elif isinstance(part, str):
                out.append(part)
        return "\n".join(x for x in out if x)
    return "" if content is None else str(content)


def strip_images(messages: List[dict]) -> List[dict]:
    """给纯文本后端兜底：把 content 数组里的图片去掉，只留文字。"""
    cleaned = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            m = dict(m)
            m["content"] = flatten_content(c)
        cleaned.append(m)
    return cleaned


def estimate_image_tokens(block_or_content: Any) -> int:
    """图片 token 估算（粗算够用）：有 detail=low 用 85，否则一图 IMAGE_EST_TOKENS_PER_IMAGE。"""
    try:
        if isinstance(block_or_content, dict) and block_or_content.get("type") == "image_url":
            detail = ((block_or_content.get("image_url") or {}).get("detail") or IMAGE_DETAIL)
            return 85 if str(detail).lower() == "low" else IMAGE_EST_TOKENS_PER_IMAGE
        if isinstance(block_or_content, list):
            return sum(estimate_image_tokens(x) for x in block_or_content)
    except Exception:
        pass
    return IMAGE_EST_TOKENS_PER_IMAGE
