"""Common LCEL scaffolding shared by all 5 pipeline agents: a
prompt | ChatOpenAI | PydanticOutputParser chain wrapped in an observability
generation span. Each agent subclasses this for its own system prompt and
output schema (Week 4's TracedLabInterpreterAgent/TracedRadiologyAgent/
TracedAllergyAgent pattern), then layers deterministic logic (regex
extraction, threshold checks, negative-scenario flags) around the LLM call.
"""
from typing import Any, TypeVar

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

ModelT = TypeVar("ModelT", bound=BaseModel)


class TracedAgent:
    agent_name: str = "base_agent"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort,
                 system_prompt: str, output_model: type[ModelT]) -> None:
        self.llm_client = llm_client
        self.observability = observability
        self.system_prompt = system_prompt
        self.output_model = output_model
        self.parser = PydanticOutputParser(pydantic_object=output_model)

    def _build_chain(self, callbacks: list):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", "{input}"),
        ]).partial(format_instructions=self.parser.get_format_instructions())
        llm = self.llm_client.chat_model(temperature=0, callbacks=callbacks)
        return prompt | llm | self.parser

    def invoke_llm(self, *, input_text: str, trace_parent: Any) -> ModelT:
        callbacks = self.observability.get_langchain_callbacks()
        generation = self.observability.start_generation(
            trace_parent, self.agent_name, model=self.llm_client.chat_model_name,
            input_data=input_text[:2000],
        )
        chain = self._build_chain(callbacks)
        try:
            result: ModelT = chain.invoke({"input": input_text})
            self.observability.end_generation(generation, output=result.model_dump())
            return result
        except Exception as exc:
            self.observability.end_generation(generation, output={"error": str(exc)})
            raise
