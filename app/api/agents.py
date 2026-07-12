from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.response import ok, fail, ErrorCode
from app.models.agent import Agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _agent_to_contract(a: Agent) -> dict:
    """Map internal Agent model to frontend contract format."""
    schema = a.input_schema_json or {}
    props = schema.get("properties", {})
    sub_func = props.get("sub_function", {})

    # Build suggests from enum values
    suggests = []
    for val in sub_func.get("enum", []):
        suggests.append({"id": f"{a.id}_{val}", "text": val})

    # Build fields from properties (excluding sub_function)
    fields = []
    for key, prop in props.items():
        if key == "sub_function":
            continue
        field = {
            "key": key,
            "label": prop.get("description", key),
            "type": "select" if "enum" in prop else ("boolean" if prop.get("type") == "boolean" else "input"),
            "defaultValue": prop.get("default", prop.get("enum", [None])[0] if "enum" in prop else ""),
        }
        if "enum" in prop:
            field["options"] = [{"label": v, "value": v} for v in prop["enum"]]
        if "placeholder" in prop:
            field["placeholder"] = prop["placeholder"]
        fields.append(field)

    return {
        "id": a.id,
        "title": a.name,
        "subtitle": a.sub_category or "",
        "group": a.sub_category or a.category,
        "iconUrl": "",
        "greeting": f"你好，我是{a.name}助手",
        "desc": f"选择功能，输入需求，AI 为你生成专业内容。",
        "suggests": suggests,
    }


@router.get("", summary="Agent 列表")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.sort_order))
    agents = result.scalars().all()
    return ok({"list": [_agent_to_contract(a) for a in agents]})


@router.get("/{agent_id}", summary="Agent 详情")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return fail(ErrorCode.NOT_FOUND, "agent 不存在")
    return ok(_agent_to_contract(agent))


@router.get("/{agent_id}/config", summary="Agent 配置")
async def get_agent_config(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return fail(ErrorCode.NOT_FOUND, "agent 不存在")

    schema = agent.input_schema_json or {}
    props = schema.get("properties", {})
    sub_func = props.get("sub_function", {})

    fields = []
    for key, prop in props.items():
        if key == "sub_function":
            continue
        field = {
            "key": key,
            "label": prop.get("description", key),
            "type": "select" if "enum" in prop else ("boolean" if prop.get("type") == "boolean" else "input"),
            "defaultValue": prop.get("default", prop.get("enum", [None])[0] if "enum" in prop else ""),
        }
        if "enum" in prop:
            field["options"] = [{"label": v, "value": v} for v in prop["enum"]]
        if prop.get("placeholder"):
            field["placeholder"] = prop["placeholder"]
        fields.append(field)

    return ok({
        "agentId": agent_id,
        "fields": fields,
        "subFunctions": sub_func.get("enum", []),
        "subFunctionGroups": sub_func.get("groups", {}),
    })
