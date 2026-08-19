from backend.llm.openai_client import OpenAIClient
from backend.observability.noop_observability import NoOpObservability


def test_noop_observability_full_lifecycle_does_not_raise():
    obs = NoOpObservability()
    trace = obs.start_trace("pipeline-run", session_id="sess-1", metadata={"report_id": 1})
    span = obs.start_span(trace, "data_extraction")
    obs.end_span(span, output={"status": "ok"})
    generation = obs.start_generation(trace, "llm-call", model="gpt-4o-mini", input_data="prompt")
    obs.end_generation(generation, output="response", usage={"total_tokens": 10})
    obs.end_span(trace)
    assert obs.get_langchain_callbacks() == []


def test_openai_client_constructs_chat_model_without_network_call():
    client = OpenAIClient(api_key="sk-fake-for-tests", chat_model="gpt-4o-mini",
                           embedding_model="text-embedding-3-small")
    chat_model = client.chat_model(temperature=0)
    assert chat_model.model_name == "gpt-4o-mini"
