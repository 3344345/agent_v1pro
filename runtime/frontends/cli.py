"""
CLI 前端：把运行时事件渲染成终端输出。

现在做得薄——只是把事件打到日志或终端。
将来 GUI 前端会写一个 gui.py，从同一份事件流渲染到窗口。
"""

from runtime.events import (
    Event,
    EVENT_STATE_CHANGED, EVENT_AGENT_STARTED, EVENT_AGENT_FINISHED,
    EVENT_TOOL_CALL, EVENT_TOOL_RESULT, EVENT_ERROR,
)


class CLIFrontend:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def __call__(self, event: Event):
        if event.type == EVENT_STATE_CHANGED:
            if self.verbose:
                print(f"  [state] {event.payload['from']} → {event.payload['to']}")

        elif event.type == EVENT_TOOL_CALL:
            name = event.payload.get("name", "?")
            print(f"🔧 {name}")

        elif event.type == EVENT_ERROR:
            print(f"❌ {event.payload.get('error', '')}")

        elif self.verbose:
            print(f"  [{event.type}] {event.payload}")