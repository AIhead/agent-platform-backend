from typing import Optional
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    icon: Mapped[str] = mapped_column(String(50), default="bot")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_json: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="agent", lazy="selectin")
