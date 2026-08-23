"""Real Langfuse adapter — built against the current Langfuse v4 SDK, which
is OTel-based (`start_observation(as_type=...)` + `.update()`/`.end()` on the
returned span/generation object). This is a materially different API from
the notebook's legacy v2-style `langfuse.trace()/.generation()` calls, not a
straight port of Week 1's traced_completion/traced_embedding helpers.
"""
import os
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Langfuse's v4 OTel-based SDK groups traces into "Sessions" by this dedicated
# span attribute (see langfuse._client.attributes.LangfuseOtelSpanAttributes.
# TRACE_SESSION_ID) — it is NOT read from the `metadata` dict. The public
# `langfuse.propagate_attributes()` helper sets it the same way, but only on
# whatever OTel span is "current" in context; this pipeline creates its root
# span explicitly (not via start_as_current_observation) and threads it as an
# explicit `parent`, so there is no ambient "current" span to propagate onto.
# Setting the attribute directly on the underlying OTel span is what makes
# the Sessions view populate.
_SESSION_ID_ATTRIBUTE = "session.id"

# Langfuse builds its OTel Resource via plain `Resource.create()` and never
# passes service.name itself, so without the standard OTEL_SERVICE_NAME env
# var every trace's resourceAttributes.service.name shows as "unknown_service".
# The OTel TracerProvider is a process-wide singleton created on first use, so
# this must be set before the first `Langfuse(...)` instantiation in-process.
_SERVICE_NAME = "clinical-intelligence-system"


class LangfuseObservability:
    def __init__(self, *, public_key: str, secret_key: str, host: str) -> None:
        os.environ.setdefault("OTEL_SERVICE_NAME", _SERVICE_NAME)
        self.client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        self.client.auth_check()

    def start_trace(self, name: str, *, session_id: str | None = None,
                     metadata: dict[str, Any] | None = None) -> Any:
        trace = self.client.start_observation(name=name, as_type="span", metadata=metadata)
        if session_id:
            trace._otel_span.set_attribute(_SESSION_ID_ATTRIBUTE, session_id)
        return trace

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
