"""Observability abstraction so agents/services never depend on a concrete
tracer. Two adapters implement this: NoOpObservability (default, used when
no Langfuse keys are configured — the app runs fully offline) and
LangfuseObservability (real, OTel-based Langfuse v4 SDK).
"""
from typing import Any, Protocol


class ObservabilityPort(Protocol):
    def start_trace(self, name: str, *, session_id: str | None = None,
                     metadata: dict[str, Any] | None = None) -> Any:
        """Starts a root trace/span. Returns an opaque observation handle."""
        ...

    def start_span(self, parent: Any, name: str, *,
                    metadata: dict[str, Any] | None = None) -> Any:
        """Starts a nested span under `parent`. Returns an opaque observation handle."""
        ...

    def end_span(self, span: Any, *, output: Any = None) -> None:
        ...

    def start_generation(self, parent: Any, name: str, *, model: str,
                          input_data: Any, metadata: dict[str, Any] | None = None) -> Any:
        """Starts a nested LLM-generation observation under `parent`."""
        ...

    def end_generation(self, generation: Any, *, output: Any = None,
                        usage: dict[str, int] | None = None) -> None:
        ...

    def get_langchain_callbacks(self) -> list:
        """Callback objects to pass as ChatOpenAI(callbacks=...) for automatic LCEL tracing."""
        ...
