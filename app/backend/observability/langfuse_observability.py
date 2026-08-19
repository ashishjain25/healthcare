"""Real Langfuse adapter — built against the current Langfuse v4 SDK, which
is OTel-based (`start_observation(as_type=...)` + `.update()`/`.end()` on the
returned span/generation object). This is a materially different API from
the notebook's legacy v2-style `langfuse.trace()/.generation()` calls, not a
straight port of Week 1's traced_completion/traced_embedding helpers.
"""
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


class LangfuseObservability:
    def __init__(self, *, public_key: str, secret_key: str, host: str) -> None:
        self.client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        self.client.auth_check()

    def start_trace(self, name: str, *, session_id: str | None = None,
                     metadata: dict[str, Any] | None = None) -> Any:
        meta = dict(metadata or {})
        if session_id:
            meta["session_id"] = session_id
        return self.client.start_observation(name=name, as_type="span", metadata=meta)

    def start_span(self, parent: Any, name: str, *,
                    metadata: dict[str, Any] | None = None) -> Any:
        return parent.start_observation(name=name, as_type="span", metadata=metadata)

    def end_span(self, span: Any, *, output: Any = None) -> None:
        if output is not None:
            span.update(output=output)
        span.end()

    def start_generation(self, parent: Any, name: str, *, model: str,
                          input_data: Any, metadata: dict[str, Any] | None = None) -> Any:
        return parent.start_observation(
            name=name, as_type="generation", model=model, input=input_data, metadata=metadata,
        )

    def end_generation(self, generation: Any, *, output: Any = None,
                        usage: dict[str, int] | None = None) -> None:
        generation.update(output=output, usage_details=usage)
        generation.end()

    def get_langchain_callbacks(self) -> list:
        return [CallbackHandler()]
