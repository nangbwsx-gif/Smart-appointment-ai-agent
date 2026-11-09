"""Model provider factory for chat LLMs and embeddings.

Supports Azure OpenAI and OpenAI-compatible providers such as Qwen,
DeepSeek, Zhipu, and OpenAI by switching environment variables.
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)
from pydantic import SecretStr

load_dotenv()


CHAT_PROVIDERS = {"openai", "qwen", "deepseek", "zhipu", "openai-compatible"}
EMBEDDING_PROVIDERS = {"openai", "qwen", "zhipu", "openai-compatible", "minimax"}


class MiniMaxEmbeddings(Embeddings):
    """MiniMax 原生 embeddings 接口：参数是 texts/type，而非 OpenAI 的 input。"""

    def __init__(self, api_key: str, base_url: str, model: str = "embo-01", batch_size: int = 32):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size

    def _embed(self, texts: list[str], type_: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            chunk = texts[start : start + self.batch_size]
            resp = requests.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model, "texts": chunk, "type": type_},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60,
            )
            resp.raise_for_status()
            vectors.extend(resp.json()["vectors"])
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "db")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def get_model_provider() -> str:
    """Return configured provider, defaulting to Azure for backward compatibility."""
    return (_env("MODEL_PROVIDER", "azure") or "azure").strip().lower()


def create_chat_model(temperature: float = 0):
    """Create a chat model from environment configuration.

    Azure-compatible env vars:
        MODEL_PROVIDER=azure
        AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT,
        AZURE_OPENAI_VERSION

    OpenAI-compatible env vars:
        MODEL_PROVIDER=qwen|deepseek|zhipu|openai|openai-compatible
        LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    """
    provider = get_model_provider()

    if provider == "azure":
        return AzureChatOpenAI(
            azure_deployment=_env("AZURE_OPENAI_DEPLOYMENT"),
            api_version=_env("AZURE_OPENAI_VERSION"),
            temperature=temperature,
            azure_endpoint=_env("AZURE_OPENAI_ENDPOINT"),
            api_key=SecretStr(_env("AZURE_OPENAI_API_KEY", "") or ""),
        )

    if provider in CHAT_PROVIDERS:
        return ChatOpenAI(
            model=_env("LLM_MODEL", "qwen-plus") or "qwen-plus",
            api_key=SecretStr(_env("LLM_API_KEY", "") or ""),
            base_url=_env("LLM_BASE_URL"),
            temperature=temperature,
        )

    raise ValueError(
        f"Unsupported MODEL_PROVIDER={provider!r}. "
        "Use azure, qwen, deepseek, zhipu, openai, or openai-compatible."
    )


def create_embedding_model():
    """Create an embedding model from environment configuration."""
    provider = (_env("EMBEDDING_PROVIDER") or get_model_provider()).strip().lower()

    if provider == "azure":
        return AzureOpenAIEmbeddings(
            azure_deployment=_env("AZURE_OPENAI_DEPLOYMENT_EMBEDDING"),
            api_key=SecretStr(_env("AZURE_OPENAI_API_KEY", "") or ""),
            api_version=_env("AZURE_OPENAI_EMBEDDING_VERSION", "2023-05-15"),
            azure_endpoint=_env("AZURE_OPENAI_ENDPOINT_EMBEDDING"),
        )

    if provider == "minimax":
        return MiniMaxEmbeddings(
            api_key=_env("EMBEDDING_API_KEY", _env("LLM_API_KEY", "")) or "",
            base_url=_env(
                "EMBEDDING_BASE_URL", _env("LLM_BASE_URL", "https://api.minimax.chat/v1")
            )
            or "",
            model=_env("EMBEDDING_MODEL", "embo-01") or "embo-01",
        )

    if provider in EMBEDDING_PROVIDERS:
        return OpenAIEmbeddings(
            model=_env("EMBEDDING_MODEL", "text-embedding-v3") or "text-embedding-v3",
            api_key=SecretStr(_env("EMBEDDING_API_KEY") or _env("LLM_API_KEY", "") or ""),
            base_url=_env("EMBEDDING_BASE_URL") or _env("LLM_BASE_URL"),
            # OpenAI-compatible providers like DashScope (Qwen) only accept raw
            # strings; disable token-id batching to send plain text.
            check_embedding_ctx_length=False,
        )

    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={provider!r}. "
        "Use azure, qwen, zhipu, openai, or openai-compatible."
    )