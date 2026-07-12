"""RAG service — supports both pgvector (PG) and in-memory (SQLite)."""
from __future__ import annotations
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge import KnowledgeDoc, KnowledgeChunk
from app.services.llm_service import create_embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def retrieve_relevant_chunks(
    db: AsyncSession,
    query: str,
    user_id: str | None = None,
    top_k: int = 3,
) -> str:
    """Retrieve relevant knowledge chunks using vector similarity search."""
    if not query:
        return ""

    try:
        query_embedding = await create_embedding(query)

        # Load all ready chunks
        stmt = (
            select(KnowledgeChunk)
            .join(KnowledgeDoc, KnowledgeChunk.doc_id == KnowledgeDoc.id)
            .where(KnowledgeDoc.status == "ready")
        )
        if user_id:
            stmt = stmt.where(KnowledgeDoc.user_id == user_id)

        result = await db.execute(stmt)
        all_chunks = result.scalars().all()

        if not all_chunks:
            return ""

        # Try pgvector cosine_distance first; fallback to in-memory
        try:
            from pgvector.sqlalchemy import Vector
            # pgvector path
            stmt2 = stmt.order_by(
                KnowledgeChunk.embedding.cosine_distance(query_embedding)
            ).limit(top_k)
            result2 = await db.execute(stmt2)
            top_chunks = result2.scalars().all()
        except Exception:
            # In-memory cosine similarity (works with SQLite/JSON)
            scored = []
            for chunk in all_chunks:
                if chunk.embedding and isinstance(chunk.embedding, list):
                    score = _cosine_similarity(query_embedding, chunk.embedding)
                    scored.append((score, chunk))
            scored.sort(key=lambda x: x[0], reverse=True)
            top_chunks = [c for _, c in scored[:top_k]]

        if not top_chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(top_chunks):
            context_parts.append(f"[参考{i+1}：{chunk.doc.title}]\n{chunk.content}")

        context_text = "\n\n---\n\n".join(context_parts)
        context_text += "\n\n**请在回答中引用知识库内容时标注来源。**"
        return context_text

    except Exception:
        return ""


async def index_document(db: AsyncSession, doc_id: str, chunks: list[str]) -> int:
    """Index document chunks with embeddings and save to DB."""
    from app.services.llm_service import create_embeddings_batch

    embeddings = await create_embeddings_batch(chunks)

    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = KnowledgeChunk(
            doc_id=doc_id,
            content=chunk_text,
            embedding=embedding,
            chunk_index=i,
        )
        db.add(chunk)

    await db.commit()
    return len(chunks)
