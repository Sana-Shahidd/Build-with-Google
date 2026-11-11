from agents import OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI

from app.config import settings

set_tracing_disabled(True)  # no OpenAI key; traces go to agent_activity instead

_clients = {
    "gemini": AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=settings.GEMINI_API_KEY or "unset",
    ),
    "groq": AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=settings.GROQ_API_KEY or "unset",
    ),
}


def provider_of(spec: str) -> str:
    return spec.split(":", 1)[0]


def build_model(spec: str) -> OpenAIChatCompletionsModel:
    """spec = 'provider:model_id', e.g. 'gemini:<flash-model-id>' (from env)."""
    provider, model_id = spec.split(":", 1)
    return OpenAIChatCompletionsModel(model=model_id, openai_client=_clients[provider])
