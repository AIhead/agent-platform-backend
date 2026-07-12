from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.sql import func

from app.models.knowledge import KnowledgeDoc, KnowledgeChunk
from app.services.llm_service import create_embedding


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
        # Create query embedding
        query_embedding = await create_embedding(query)

        # Vector similarity search
        stmt = (
            select(KnowledgeChunk)
            .join(KnowledgeDoc, KnowledgeChunk.doc_id == KnowledgeDoc.id)
            .where(KnowledgeDoc.status == "ready")
        )
        if user_id:
            stmt = stmt.where(KnowledgeDoc.user_id == user_id)

        stmt = stmt.order_by(
            KnowledgeChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return ""

        # Format context with citation markers
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[参考{i+1}：{chunk.doc.title}]\n{chunk.content}")

        context_text = "\n\n---\n\n".join(context_parts)
        context_text += "\n\n**请在回答中引用知识库内容时标注来源。**"

        return context_text

    except Exception:
        # Graceful degradation — if embeddings/vector search fails, skip RAG
        return ""


async def index_document(db: AsyncSession, doc_id: str, chunks: list[str]) -> int:
    """Index document chunks with embeddings and save to DB."""
    from app.services.llm_service import create_embeddings_batch

    # Batch create embeddings
    embeddings = await create_embeddings_batch(chunks)

    # Save chunks
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
