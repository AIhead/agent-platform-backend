from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AgentResponse(BaseModel):
    id: str
    name: str
    category: str
    sub_category: str | None
    icon: str
    system_prompt: str
    input_schema_json: dict | None
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    categories: list[str]


class AgentRunRequest(BaseModel):
    agent_id: str
    conversation_id: str | None = None  # None = 新建会话
    params: dict = Field(default_factory=dict)  # 用户填写的参数 {style: "爆款吸睛", ...}
    user_message: str = ""  # 用户自由输入的问题/主题
