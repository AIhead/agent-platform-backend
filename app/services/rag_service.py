"""RAG service — vector similarity search via pgvector."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge import KnowledgeDoc, KnowledgeChunk
from app.services.llm_service import create_embedding, create_embeddings_batch


async def retrieve_relevant_chunks(
    db: AsyncSession,
    query: str,
    user_id: str | None = None,
    top_k: int = 3,
) -> str:
    """Retrieve relevant knowledge chunks using pgvector cosine distance."""
    if not query:
        return ""

    try:
        query_embedding = await create_embedding(query)

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

        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[参考{i+1}：{chunk.doc.title}]\n{chunk.content}")

        return "\n\n---\n\n".join(context_parts) + "\n\n**请在回答中引用知识库内容时标注来源。**"

    except Exception:
        return ""


async def index_document(db: AsyncSession, doc_id: str, chunks: list[str]) -> int:
    """Index document chunks with embeddings and save to DB."""
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
