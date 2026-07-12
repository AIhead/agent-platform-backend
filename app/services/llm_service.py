from __future__ import annotations
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

# DeepSeek client (OpenAI-compatible)
deepseek_client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
)

# Lazy-loaded local embedding model
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _embedding_model


async def chat_completion(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Non-streaming chat completion via DeepSeek."""
    response = await deepseek_client.chat.completions.create(
        model=model or settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def chat_completion_stream(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Streaming chat completion via DeepSeek, yields text chunks."""
    stream = await deepseek_client.chat.completions.create(
        model=model or settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def create_embedding(text: str) -> list[float]:
    """Create embedding vector using local BGE model."""
    model = _get_embedding_model()
    # sentence-transformers runs synchronously; wrap in thread for async compat
    import asyncio
    embedding = await asyncio.to_thread(
        lambda: model.encode(text, normalize_embeddings=True).tolist()
    )
    return embedding


async def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Create embeddings for multiple texts using local BGE model."""
    model = _get_embedding_model()
    import asyncio
    embeddings = await asyncio.to_thread(
        lambda: model.encode(texts, normalize_embeddings=True).tolist()
    )
    return embeddings
