import json
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, async_session_factory
from app.core.deps import get_current_user
from app.core.response import ok, fail, ErrorCode
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation, Message
from app.services.agent_service import run_agent_stream

router = APIRouter(prefix="/api", tags=["conversations"])


def _conv_to_contract(c) -> dict:
    return {
        "id": c.id,
        "agentId": c.agent_id,
        "title": c.title,
        "preview": getattr(c, "preview", ""),
        "updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000),
    }


# === Conversations ===

@router.get("/conversations", summary="对话列表")
async def list_conversations(
    agent_id: Optional[str] = Query(None, alias="agentId"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg_count_subq = (
        select(Message.conversation_id, func.count(Message.id).label("cnt"))
        .group_by(Message.conversation_id).subquery()
    )
    stmt = (
        select(Conversation, Agent.name, func.coalesce(msg_count_subq.c.cnt, 0))
        .outerjoin(msg_count_subq, Conversation.id == msg_count_subq.c.conversation_id)
        .join(Agent, Conversation.agent_id == Agent.id)
        .where(Conversation.user_id == user.id)
    )
    if agent_id:
        stmt = stmt.where(Conversation.agent_id == agent_id)
    stmt = stmt.order_by(Conversation.updated_at.desc())

    result = await db.execute(stmt)
    rows = result.all()

    return ok({"list": [
        {
            "id": conv.id,
            "agentId": conv.agent_id,
            "title": conv.title,
            "preview": "",
            "updatedAt": int(conv.updated_at.timestamp() * 1000),
        }
        for conv, _, _ in rows
    ]})


@router.post("/conversations", summary="创建对话")
async def create_conversation(data: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent_id = data.get("agentId") or data.get("agent_id")
    if not agent_id:
        return fail(ErrorCode.PARAM_ERROR, "agentId 必传")

    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        return fail(ErrorCode.NOT_FOUND, "agent 不存在")

    conv = Conversation(user_id=user.id, agent_id=agent_id, title="新对话")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ok({
        "id": conv.id,
        "agentId": conv.agent_id,
        "title": conv.title,
        "preview": "",
        "createdAt": int(conv.created_at.timestamp() * 1000),
        "updatedAt": int(conv.updated_at.timestamp() * 1000),
    })


@router.get("/conversations/{conv_id}", summary="对话消息列表")
async def get_messages(conv_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    conv = (await db.execute(select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id))).scalar_one_or_none()
    if not conv:
        return fail(ErrorCode.NOT_FOUND, "对话不存在")

    msgs = (await db.execute(select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at))).scalars().all()
    return ok({
        "id": conv.id,
        "agentId": conv.agent_id,
        "title": conv.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "status": "sent",
                "createdAt": int(m.created_at.timestamp() * 1000),
            }
            for m in msgs
        ],
    })


# === Chat Messages (SSE streaming) ===

@router.post("/chat/messages", summary="发送消息（SSE 流式）")
async def send_message(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent_id = data.get("agentId") or data.get("agent_id", "")
    conversation_id = data.get("conversationId") or data.get("conversation_id")
    content = data.get("content", "")
    suggest_id = data.get("suggestId", "")

    if not agent_id or not conversation_id:
        return fail(ErrorCode.PARAM_ERROR, "agentId 和 conversationId 必传")

    # Get or verify conversation
    conv = (await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))).scalar_one_or_none()
    if not conv:
        return fail(ErrorCode.NOT_FOUND, "对话不存在")

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=content or suggest_id)
    db.add(user_msg)
    await db.commit()

    # Update title from first message
    if conv.title == "新对话" and content:
        conv.title = content[:50]
        await db.commit()

    _conv_id = conv.id
    _user_id = user.id

    async def event_generator():
        async with async_session_factory() as stream_db:
            full_response = ""
            try:
                params = {"sub_function": suggest_id} if suggest_id else {}
                async for chunk in run_agent_stream(db=stream_db, agent_id=agent_id, params=params, user_message=content, user_id=_user_id):
                    full_response += chunk
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            if full_response:
                assistant_msg = Message(conversation_id=_conv_id, role="assistant", content=full_response)
                stream_db.add(assistant_msg)
                await stream_db.commit()

            yield f"data: {json.dumps({'done': True, 'conversation_id': _conv_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
