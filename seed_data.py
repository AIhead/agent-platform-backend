"""Seed the database with initial agent definitions."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.models.agent import Agent
from app.core.database import Base

settings = get_settings()

AGENTS = [
    # ===== Agent 1: 商业咨询导师 =====
    {
        "id": "728c6cdd-1faa-50dc-9876-56e8c72f45b2",
        "name": "商业咨询导师",
        "category": "多智能体功能",
        "sub_category": "商业咨询导师",
        "icon": "target",
        "system_prompt": "{sub_function_prompt}",
        "input_schema_json": {
            "type": "object",
            "properties": {
                "sub_function": {
                    "type": "string", "description": "选择功能",
                    "enum": [
                        "商业定位咨询",
                        "产品矩阵设计",
                        "超级内容操盘手"
                    ]
                },
            },
            "required": ["sub_function"]
        },
        "sort_order": 1,
    },
    # ===== Agent 2: 获客高手 =====
    {
        "id": "b5c0c88e-b846-50ed-842c-02bc5d8a733c",
        "name": "获客高手",
        "category": "多智能体功能",
        "sub_category": "获客高手",
        "icon": "video",
        "system_prompt": "{sub_function_prompt}",
        "input_schema_json": {
            "type": "object",
            "properties": {
                "sub_function": {
                    "type": "string", "description": "选择功能",
                    "enum": ["短视频文案", "直播获客策略", "直播脚本"],
                    "groups": {
                        "短视频文案": ["platform", "style", "keywords", "content_type", "duration", "tone", "add_interaction"],
                        "直播获客策略": [],
                        "直播脚本": ["product_name", "duration"]
                    }
                },
                # 短视频参数
                "platform": {"type": "string", "description": "目标平台", "enum": ["抖音", "视频号", "小红书"]},
                "style": {"type": "string", "description": "风格", "enum": ["爆款吸睛", "干货科普", "悬念引导"]},
                "keywords": {"type": "string", "description": "核心关键词"},
                "content_type": {"type": "string", "description": "文案类型", "enum": ["口播稿", "字幕文案", "产品卖点文案"]},
                "duration": {"type": "integer", "description": "时长", "enum": [15, 30, 60]},
                "tone": {"type": "string", "description": "语气设定", "enum": ["活泼", "严肃", "专业"]},
                "add_interaction": {"type": "boolean", "description": "添加互动引导"},
                # 直播参数
                "live_desc": {"type": "string", "description": "描述你的人设和业务"},
                "product_name": {"type": "string", "description": "产品/服务名称"},
                "target_users": {"type": "string", "description": "目标用户群体"},
            },
            "required": ["sub_function"]
        },
        "sort_order": 2,
    },
    # ===== Agent 3: 成交转化 =====
    {
        "id": "4bfa5a81-a4ad-570c-a7d7-121090a92ec2",
        "name": "成交转化",
        "category": "多智能体功能",
        "sub_category": "成交转化",
        "icon": "message-circle",
        "system_prompt": "{sub_function_prompt}",
        "input_schema_json": {
            "type": "object",
            "properties": {
                "sub_function": {
                    "type": "string", "description": "选择功能",
                    "enum": ["朋友圈文案"],
                    "groups": {
                        "朋友圈文案": ["topic", "scene", "style"]
                    }
                },
                "topic": {"type": "string", "description": "产品/主题"},
                "scene": {"type": "string", "description": "使用场景", "enum": ["产品推广", "节日祝福", "日常分享"]},
                "style": {"type": "string", "description": "文案风格", "enum": ["温情走心", "幽默风趣", "专业干货", "励志向上"]},
                "product_name": {"type": "string", "description": "产品/服务名称"},
                "target_users": {"type": "string", "description": "目标用户群体"},
                "duration": {"type": "integer", "description": "直播时长(分钟)", "enum": [30, 60, 120]},
            },
            "required": ["sub_function"]
        },
        "sort_order": 3,
    },
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        for a in AGENTS:
            result = await session.execute(select(Agent).where(Agent.id == a["id"]))
            existing = result.scalar_one_or_none()
            if existing:
                for key, val in a.items():
                    setattr(existing, key, val)
                print(f"Updated: {a['name']}")
            else:
                session.add(Agent(**a))
                print(f"Created: {a['name']}")
        await session.commit()
        print(f"Seeded {len(AGENTS)} agents (upsert).")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
