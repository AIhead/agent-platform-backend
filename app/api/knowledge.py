from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import ok, fail, ErrorCode
from app.models.user import User
from app.models.knowledge import KnowledgeDoc, KnowledgeChunk
from app.services.file_service import save_upload_file, extract_text, chunk_text, allowed_file
from app.services.rag_service import index_document

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

ADMIN_PHONES = {"13800138000"}

async def require_admin(user: User = Depends(get_current_user)):
    if user.phone not in ADMIN_PHONES:
        raise HTTPException(status_code=403, detail="仅管理员可操作知识库")
    return user


def _doc_response(doc: KnowledgeDoc) -> dict:
    return {"id": doc.id, "title": doc.title, "fileType": doc.file_type, "status": doc.status, "createdAt": int(doc.created_at.timestamp() * 1000)}


@router.get("", summary="文档列表")
async def list_docs(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KnowledgeDoc).where(KnowledgeDoc.user_id == user.id).order_by(KnowledgeDoc.created_at.desc()))
    return ok({"list": [_doc_response(d) for d in result.scalars().all()]})


@router.post("/upload", summary="上传文档（管理员）")
async def upload_doc(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    if not allowed_file(file.content_type or ""):
        return fail(ErrorCode.PARAM_ERROR, f"不支持的文件类型: {file.content_type}")
    try:
        file_path = await save_upload_file(file)
    except ValueError as e:
        return fail(ErrorCode.PARAM_ERROR, str(e))

    doc = KnowledgeDoc(user_id=user.id, title=file.filename or "untitled", file_type=file.content_type or "unknown", file_url=file_path, status="processing")
    db.add(doc); await db.commit(); await db.refresh(doc)
    try:
        text = extract_text(file_path, doc.file_type)
        chunks = chunk_text(text)
        count = await index_document(db, doc.id, chunks)
        doc.status = "ready"; await db.commit(); await db.refresh(doc)
        return ok({"id": doc.id, "title": doc.title, "fileType": doc.file_type, "status": doc.status, "chunkCount": count})
    except Exception as e:
        doc.status = "error"; await db.commit()
        return fail(ErrorCode.SERVER_ERROR, f"处理失败: {str(e)}")


@router.delete("/{doc_id}", summary="删除文档（管理员）")
async def delete_doc(doc_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    doc = (await db.execute(select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id, KnowledgeDoc.user_id == user.id))).scalar_one_or_none()
    if not doc: return fail(ErrorCode.NOT_FOUND, "文档不存在")
    await db.delete(doc); await db.commit()
    return ok()


@router.post("/search", summary="全文搜索")
async def search_docs(keyword: str = Query(default=""), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not keyword.strip(): return ok({"results": []})
    result = await db.execute(select(KnowledgeChunk).join(KnowledgeDoc).where(KnowledgeDoc.user_id == user.id, KnowledgeDoc.status == "ready", KnowledgeChunk.content.ilike(f"%{keyword}%")).limit(20))
    chunks = result.scalars().all()
    doc_map = {}
    for chunk in chunks:
        if chunk.doc_id not in doc_map:
            doc_map[chunk.doc_id] = {"docId": chunk.doc_id, "docTitle": chunk.doc.title if chunk.doc else "Unknown", "snippets": []}
        text = chunk.content; idx = text.lower().find(keyword.lower())
        start = max(0, idx - 30); end = min(len(text), idx + len(keyword) + 50)
        doc_map[chunk.doc_id]["snippets"].append(("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else ""))
    return ok({"results": list(doc_map.values())})


@router.post("/batch-delete", summary="批量删除（管理员）")
async def batch_delete(ids: list[str] = Query(default=[]), db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    if not ids: return fail(ErrorCode.PARAM_ERROR, "No IDs")
    for doc_id in ids:
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc_id))
    result = await db.execute(delete(KnowledgeDoc).where(KnowledgeDoc.id.in_(ids), KnowledgeDoc.user_id == user.id))
    await db.commit()
    return ok({"deleted": result.rowcount})
