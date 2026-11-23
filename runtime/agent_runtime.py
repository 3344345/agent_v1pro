"""
AgentRuntime：控制层。

批 4 改造：
- submit_async() 起工作线程，立刻返回
- stop() 停止按钮，机械停止 < 5s
- 不引入 PAUSED 状态——停止就是任务被打断，回 IDLE
"""

import threading
from typing import Callable, List, Optional

from runtime.state import AgentState, can_transition
from runtime.events import (
    Event,
    EVENT_USER_INPUT, EVENT_STATE_CHANGED,
    EVENT_AGENT_STARTED, EVENT_AGENT_FINISHED,
    EVENT_ERROR,
)
from runtime.stop_token import StopToken, set_current, StopException  # 新增 StopException
from logger import log_event


HandlerFn = Callable[[str, "AgentRuntime"], None]


class AgentRuntime:
    def __init__(self, handler: HandlerFn):
        self._state = AgentState.IDLE
        self._state_lock = threading.Lock()
        self._subscribers: List[Callable[[Event], None]] = []
        self._handler = handler
        self._last_user_input: Optional[str] = None
        self._stop_token: Optional[StopToken] = None
        self._worker: Optional[threading.Thread] = None

    # ---------- 状态 ----------
    @property
    def state(self) -> AgentState:
        with self._state_lock:
            return self._state

    @property
    def stop_token(self) -> Optional[StopToken]:
        """给 handler / run_agent 访问当前停止令牌"""
        return self._stop_token

    def status(self) -> dict:
        return {
            "state": self.state.value,
            "last_user_input": self._last_user_input,
            "busy": self.is_busy(),
        }

    def is_busy(self) -> bool:
        """worker 槽位被占用即为忙。槽位在状态回 IDLE 之后才释放，
        因此 is_busy()==False 时状态必然是 IDLE，前端不会看到"空闲但状态未归位"。"""
        return self._worker is not None

    def _set_state(self, new_state: AgentState):
        with self._state_lock:
            if new_state == self._state:
                return
            if not can_transition(self._state, new_state):
                log_event("warning",
                          f"非法状态转移: {self._state.value} → {new_state.value}",
                          stage="runtime", event="state.illegal")
                return
            old = self._state
            self._state = new_state

        log_event("debug",
                  f"状态转移: {old.value} → {new_state.value}",
                  stage="runtime", event="state.changed",
                  extra={"from": old.value, "to": new_state.value})

        self._broadcast(Event(
            type=EVENT_STATE_CHANGED,
            payload={"from": old.value, "to": new_state.value},
        ))

    # ---------- 事件订阅 ----------
    def subscribe(self, callback: Callable[[Event], None]):
        self._subscribers.append(callback)

        def unsubscribe():
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    def _broadcast(self, event: Event):
        for cb in self._subscribers:
            try:
                cb(event)
            except Exception as e:
                log_event("warning",
                          f"事件订阅者异常: {e}",
                          stage="runtime", event="subscriber.error")

    # ---------- 提交 ----------
    def submit_async(self, user_input: str, images=None) -> bool:
        """异步提交，立刻返回。返回 False 表示拒绝（任务已在跑）。images 为图片路径列表。

        准入判定与 worker 槽位分配在同一把锁内完成，杜绝"放行后又被静默丢弃"的窗口。
        """
        with self._state_lock:
            if self._state != AgentState.IDLE or self._worker is not None:
                rejected_state = self._state.value
            else:
                rejected_state = None
                self._worker = threading.Thread(
                    target=self._run,
                    args=(user_input, images),
                    daemon=True,
                    name="agent-worker",
                )
                self._worker.start()

        # 日志一律在锁外写：logger 有 IO，锁内写会拖住整个状态机
        if rejected_state is not None:
            log_event("warning",
                      f"当前状态 {rejected_state}，拒绝新输入",
                      stage="runtime", event="submit.rejected")
            return False
        return True

    def stop(self) -> bool:
        """停止按钮。返回是否真的发出了停止信号。"""
        token = self._stop_token
        if token is None or not self.is_busy():
            return False
        log_event("info", "收到停止请求", stage="runtime", event="stop.request")
        token.stop()
        return True

    # ---------- 内部：工作线程入口 ----------
    def _run(self, user_input: str, images=None):
        # 准入已在 submit_async 的锁内完成，这里只做初始化
        with self._state_lock:
            self._stop_token = StopToken()

        # 让 executor 能通过 get_current() 拿到
        set_current(self._stop_token)
        self._last_user_input = user_input

        self._broadcast(Event(
            type=EVENT_USER_INPUT,
            payload={"text": user_input},
        ))

        stopped = False
        try:
            self._set_state(AgentState.PREPARING)
            self._broadcast(Event(
                type=EVENT_AGENT_STARTED,
                payload={"user_input": user_input},
            ))

            self._set_state(AgentState.RUNNING)
            self._handler(user_input, self, images=images)

            stopped = self._stop_token.is_stopped()
        except StopException:
            # 用户主动停止导致的异常
            stopped = True
            log_event("info", "任务被用户中断", stage="runtime", event="stop.interrupted")
        except Exception as e:
            # 检查异常是否是因为用户按了 stop 导致的
            if self._stop_token and self._stop_token.is_stopped():
                stopped = True
                log_event("info", "任务因用户中断抛出异常，转入取消状态", stage="runtime", event="stop.interrupted")
            else:
                # 真正的系统崩溃
                log_event("error", f"运行时异常: {e}",
                          stage="runtime", event="runtime.error")
                self._broadcast(Event(
                    type=EVENT_ERROR,
                    payload={"error": str(e)},
                ))
                self._set_state(AgentState.ERROR)
        finally:
            set_current(None)

        # 状态收尾（在锁外做，避免死锁）
        current_state = self.state
        if current_state in (AgentState.PREPARING, AgentState.RUNNING):
            if stopped:
                self._set_state(AgentState.CANCELLED)
            else:
                self._set_state(AgentState.DONE)

            self._broadcast(Event(
                type=EVENT_AGENT_FINISHED,
                payload={"status": "stopped" if stopped else "done"},
            ))
            self._set_state(AgentState.IDLE)
        elif current_state == AgentState.ERROR:
            self._set_state(AgentState.IDLE)

        # 释放 worker 槽位。is_busy() 以槽位为准，而槽位只在状态已回 IDLE 后才清空，
        # 因此外部永远看不到"状态已 IDLE 但 is_busy() 仍为 True"的中间态。
        # 注意：这里只做赋值，绝不调用 _set_state（它会再取同一把非重入锁 → 自锁）。
        with self._state_lock:
            self._stop_token = None
            self._worker = None