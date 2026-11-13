from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from logger import log_event

@dataclass
class GuardrailContext:
    messages: List[dict]
    tool_name: str
    tool_args: dict
    output: str
    state: dict
    history: list

class BaseGuardrail(ABC):
    name: str = "BaseGuardrail"

    @abstractmethod
    def inspect(self, ctx: GuardrailContext) -> Optional[str]:
        return None

class GuardrailEngine:
    def __init__(self):
        self.guardrails: List[BaseGuardrail] = []
        self.state = {}

    def register(self, guardrail: BaseGuardrail):
        self.guardrails.append(guardrail)

    def check(self, messages: list, tool_name: str, tool_args: dict, output: str, history: list) -> bool:
        for g in self.guardrails:
            ctx = GuardrailContext(
                messages=messages, tool_name=tool_name, tool_args=tool_args,
                output=output, state=self.state, history=history
            )
            result = g.inspect(ctx)
            if result:
                print(f"\n🛡️ [护栏熔断] {g.name} 触发！")
                print(f"   ↳ 干预指令: {result[:50]}...\n")
                
                log_event("warning", f"Guardrail Triggered: {g.name}", 
                          stage="guardrail", event="guardrail.trigger",
                          extra={"tool": tool_name, "args": tool_args, "intervention": result})
                
                messages.append({"role": "user", "content": result})
                return True
        return False