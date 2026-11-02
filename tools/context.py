from typing import Optional, List, Dict


class ToolContext:
    def __init__(self):
        self.last_search_results: Optional[List[Dict]] = None
        self.todos: Optional[List[Dict]] = None

    def reset(self):
        self.last_search_results = None
        self.todos = None


_ctx = ToolContext()


def get_context() -> ToolContext:
    return _ctx