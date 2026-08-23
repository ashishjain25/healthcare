"""Verifies LangfuseObservability's control flow against a stub that mimics
the real Langfuse v4 SDK's surface (start_observation returning an object
with .update()/.end()/.start_observation()), confirmed by direct introspection
of the installed langfuse==4.14.1 package. No live Langfuse credentials are
available in this environment, so this cannot hit the real network — it
proves the adapter calls the right methods with the right shapes, not that
traces actually land in a Langfuse project.
"""
from backend.observability.langfuse_observability import LangfuseObservability


class _StubOtelSpan:
    def __init__(self):
        self.attributes = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value


class _StubObservation:
    def __init__(self, name):
        self.name = name
        self.updates = []
        self.ended = False
        self.children = []
        self._otel_span = _StubOtelSpan()

    def start_observation(self, *, name, as_type, **kwargs):
        child = _StubObservation(name)
        self.children.append((as_type, child, kwargs))
        return child

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self):
        self.ended = True


class _StubLangfuseClient:
    def __init__(self):
        self.roots = []

    def start_observation(self, *, name, as_type, **kwargs):
        root = _StubObservation(name)
        self.roots.append((as_type, root, kwargs))
        return root


def _build_adapter() -> LangfuseObservability:
    adapter = LangfuseObservability.__new__(LangfuseObservability)
    adapter.client = _StubLangfuseClient()
    return adapter


def test_start_trace_creates_root_span_with_session_id():
    adapter = _build_adapter()
    trace = adapter.start_trace("pipeline-run", session_id="sess-1", metadata={"report_id": 1})

    as_type, root, kwargs = adapter.client.roots[0]
    assert as_type == "span"
    assert kwargs["metadata"] == {"report_id": 1}
    assert root._otel_span.attributes["session.id"] == "sess-1"
    assert trace is root


def test_span_lifecycle_updates_and_ends():
    adapter = _build_adapter()
    trace = adapter.start_trace("pipeline-run")
    span = adapter.start_span(trace, "stage-1", metadata={"x": 1})
    adapter.end_span(span, output={"status": "ok"})

    assert span.updates == [{"output": {"status": "ok"}}]
    assert span.ended is True


def test_generation_lifecycle_passes_model_and_usage():
    adapter = _build_adapter()
    trace = adapter.start_trace("pipeline-run")
    generation = adapter.start_generation(trace, "llm-call", model="gpt-4o-mini", input_data="prompt text")
    adapter.end_generation(generation, output="response text", usage={"total_tokens": 42})

    as_type, _, kwargs = trace.children[0]
    assert as_type == "generation"
    assert kwargs["model"] == "gpt-4o-mini"
    assert generation.updates == [{"output": "response text", "usage_details": {"total_tokens": 42}}]
    assert generation.ended is True
