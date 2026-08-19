"""Default observability adapter — used whenever LANGFUSE_* keys are absent
so the whole app (including the agent pipeline) runs fully offline."""
from typing import Any


class _NoOpObservation:
    __slots__ = ()


_HANDLE = _NoOpObservation()


class NoOpObservability:
    def start_trace(self, name: str, *, session_id: str | None = None,
                     metadata: dict[str, Any] | None = None) -> Any:
        return _HANDLE

    def start_span(self, parent: Any, name: str, *,
                    metadata: dict[str, Any] | None = None) -> Any:
        return _HANDLE

    def end_span(self, span: Any, *, output: Any = None) -> None:
        return None

    def start_generation(self, parent: Any, name: str, *, model: str,
                          input_data: Any, metadata: dict[str, Any] | None = None) -> Any:
        return _HANDLE

    def end_generation(self, generation: Any, *, output: Any = None,
                        usage: dict[str, int] | None = None) -> None:
        return None

    def get_langchain_callbacks(self) -> list:
        return []
