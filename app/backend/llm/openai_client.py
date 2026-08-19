"""Injectable OpenAI wrapper — embeddings + a ChatOpenAI factory. Replaces
Week 1's module-global `openai_client`/`traced_embedding`/`traced_completion`
with a constructor-injected object; tracing is applied by the caller via
ObservabilityPort, not baked in here.
"""
from langchain_openai import ChatOpenAI
from openai import OpenAI


class OpenAIClient:
    def __init__(self, *, api_key: str, chat_model: str, embedding_model: str) -> None:
        # The openai SDK (v2.x) raises at construction time if api_key is falsy,
        # even though this app must be constructible with no key configured (the
        # "runs fully offline" startup path) — routers gate real calls behind
        # settings.openai_configured before ever reaching this client.
        self.api_key = api_key
        self.chat_model_name = chat_model
        self.embedding_model_name = embedding_model
        self._client = OpenAI(api_key=api_key or "sk-not-configured")

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self.embedding_model_name, input=text)
        return response.data[0].embedding

    def chat_model(self, *, temperature: float = 0, callbacks: list | None = None) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.chat_model_name,
            temperature=temperature,
            api_key=self.api_key,
            callbacks=callbacks or [],
        )

    def complete(self, *, prompt: str, system: str = "", temperature: float = 0) -> str:
        """Plain chat completion, no structured-output parser — used by the chatbot."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self.chat_model_name, messages=messages, temperature=temperature,
        )
        return response.choices[0].message.content or ""
