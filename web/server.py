#!/usr/bin/env python3
"""
Agent V1 Pro — Web UI 服务（标准库实现，无第三方依赖）

设计原则（低耦合）：
1. 控制层完全复用 runtime.AgentRuntime，任务执行复用 main.handle_input
   —— 不复制 agent 循环，不改 core 任何一行。
2. 事件流不侵入业务：只增量 tail logs/agent.jsonl（logger 已是结构化事件源）。
3. 前端零构建：web/static 下的原生 HTML/CSS/JS。

启动：
    python web/server.py --port 8123
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(WEB_DIR)
STATIC_DIR = os.path.join(WEB_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
sys.path.insert(0, PROJ_DIR)

from config import LOG_FILE                      # noqa: E402
from main import handle_input                    # noqa: E402
from runtime.agent_runtime import AgentRuntime   # noqa: E402

runtime = AgentRuntime(handler=handle_input)
_submit_lock = threading.Lock()

MAX_EVENT_CHARS = 6000          # 单条事件推送上限，避免 SSE 卡死
PUSH_STAGES = {"tool_call", "tool_result", "reply", "route", "confirm", "llm", "input"}
PUSH_RUNTIME_PREFIX = ("state.", "stop.", "runtime.error", "submit.rejected")


# --------------------------------------------------------------------------
# 日志 → 前端事件 的映射（唯一耦合点，集中在 classify_event）
# --------------------------------------------------------------------------
def classify_event(rec: dict):
    stage = rec.get("stage") or ""
    event = rec.get("event") or ""
    msg = rec.get("message") or ""
    extra = rec.get("extra") or {}

    if stage == "tool_call":
        return "tool_call", {
            "tool": extra.get("tool") or _guess_tool(msg),
            "args": extra.get("args"),
            "text": msg,
        }
    if stage == "tool_result":
        return "tool_result", {
            "tool": extra.get("tool") or _guess_tool(msg),
            "text": msg[:MAX_EVENT_CHARS],
            "level": rec.get("level"),
        }
    if stage == "reply":
        return "reply", {"text": msg}
    if stage == "route":
        return "route", {"text": msg}
    if stage == "confirm":
        return "confirm", {"text": msg, "event": event}
    if stage == "runtime" and event.startswith(PUSH_RUNTIME_PREFIX):
        return "runtime", {"text": msg, "event": event}
    if stage == "llm" and event in ("llm.done", "llm.error"):
        return "llm", {"text": msg, "event": event}
    return None, None


def _guess_tool(msg: str) -> str:
    if ":" in msg:
        head = msg.split(":", 1)[1].strip()
        return head.split(",")[0].split(" ")[0] or "tool"
    return "tool"


# --------------------------------------------------------------------------
# HTTP 处理
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AgentWebUI/1.0"

    def log_message(self, fmt, *args):      # 静默访问日志
        pass

    # ---------------- 基础响应 ----------------
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not os.path.isfile(path):
            self._send_json({"error": "not found"}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------------- GET ----------------
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path

        if path in ("/", "/index.html"):
            return self._send_file(os.path.join(STATIC_DIR, "index.html"))
        if path.startswith("/static/"):
            safe = os.path.normpath(path[len("/static/"):]).lstrip("/")
            return self._send_file(os.path.join(STATIC_DIR, safe))
        if path == "/api/status":
            return self._send_json({
                "busy": runtime.is_busy(),
                "state": getattr(runtime.state, "value", str(runtime.state)),
            })
        if path == "/api/chat/stream":
            return self._handle_stream(parse_qs(u.query))

        self._send_json({"error": "not found"}, 404)

    # ---------------- POST ----------------
    def do_POST(self):
        u = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._send_json({"error": "bad json"}, 400)

        if u.path == "/api/upload":
            # 接收 {name, dataUrl} 或 {name, base64}，存盘后返回绝对路径
            data_url = data.get("dataUrl") or data.get("base64") or ""
            name = (data.get("name") or "image.png").strip()
            if not data_url:
                return self._send_json({"error": "empty image"}, 400)
            try:
                if "," in data_url and data_url.strip().lower().startswith("data:"):
                    header, b64 = data_url.split(",", 1)
                    ext = "png"
                    if "jpeg" in header or "jpg" in header:
                        ext = "jpg"
                    elif "webp" in header:
                        ext = "webp"
                    elif "gif" in header:
                        ext = "gif"
                else:
                    b64 = data_url
                    ext = os.path.splitext(name)[1].lstrip(".").lower() or "png"
                raw_bytes = base64.b64decode(b64)
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                fname = f"up_{int(time.time()*1000)}_{os.getpid()}.{ext}"
                fpath = os.path.join(UPLOAD_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(raw_bytes)
                return self._send_json({"ok": True, "path": fpath})
            except Exception as e:
                return self._send_json({"error": f"upload failed: {e}"}, 400)

        if u.path == "/api/chat":
            msg = (data.get("message") or "").strip()
            images = data.get("images") or []
            print(f"[INBOUND] /api/chat message={msg!r} images={images!r}", flush=True)
            if not isinstance(images, list):
                images = []
            images = [str(x) for x in images if str(x).strip()]
            if not msg and not images:
                return self._send_json({"error": "empty message"}, 400)
            with _submit_lock:
                offset = _log_size()
                ok = runtime.submit_async(msg, images=images)
            if not ok:
                return self._send_json({"error": "busy", "offset": offset}, 409)
            return self._send_json({"ok": True, "offset": offset})

        if u.path == "/api/stop":
            return self._send_json({"ok": runtime.stop()})

        self._send_json({"error": "not found"}, 404)

    # ---------------- SSE ----------------
    def _handle_stream(self, qs):
        try:
            offset = int((qs.get("offset") or ["0"])[0])
        except ValueError:
            offset = 0

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        def push(kind, payload):
            try:
                self.wfile.write(
                    ("event: " + kind + "\ndata: " +
                     json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        start = _log_size()
        offset = max(0, min(offset, start))
        try:
            f = open(LOG_FILE, "rb")
        except FileNotFoundError:
            return
        f.seek(offset)
        buf = b""
        idle_since = None
        last_ping = time.time()
        deadline = time.time() + 3600

        try:
            while time.time() < deadline:
                chunk = f.read(262144)
                if chunk:
                    buf += chunk
                    lines = buf.split(b"\n")
                    buf = lines.pop()
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line.decode("utf-8", "ignore"))
                        except Exception:
                            continue
                        kind, payload = classify_event(rec)
                        if kind and not push(kind, payload):
                            return
                    idle_since = None
                else:
                    if not runtime.is_busy():
                        if idle_since is None:
                            idle_since = time.time()
                        elif time.time() - idle_since > 0.8:
                            push("end", {"offset": f.tell()})
                            return
                    else:
                        idle_since = None
                    if time.time() - last_ping > 10:
                        try:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                        except Exception:
                            return
                        last_ping = time.time()
                    time.sleep(0.12)
            push("end", {"offset": f.tell()})
        finally:
            f.close()


def _log_size():
    try:
        return os.path.getsize(LOG_FILE)
    except OSError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8123)
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    print(f"🌐 Agent Web UI: http://{args.host}:{args.port}")
    print(f"   事件源: {LOG_FILE}")
    print("   Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
