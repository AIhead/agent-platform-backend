from fastapi import APIRouter, Query
from app.core.response import ok

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

TEMPLATES = {
    "商业咨询导师": [
        {"title": "SaaS 产品商业分析", "prompt": "分析一款面向中小企业的SaaS产品"},
        {"title": "产品矩阵设计", "prompt": "为我的产品设计引流品+利润品+增值品的完整矩阵"},
        {"title": "内容营销体系", "prompt": "搭建内容营销体系，包含选题策略和多平台分发方案"},
    ],
    "获客高手": [
        {"title": "短视频爆款文案", "prompt": "用爆款吸睛风格在抖音生成一条60秒口播文案"},
        {"title": "直播带货脚本", "prompt": "设计一场完整直播，包含开场/干货/产品/收尾脚本"},
        {"title": "直播获客策略", "prompt": "制定直播获客方案，包含人设定位和引流转化策略"},
    ],
    "成交转化": [
        {"title": "新品上市朋友圈", "prompt": "为新品写一条朋友圈推广文案"},
        {"title": "社群成交话术", "prompt": "设计社群成交话术"},
        {"title": "用户见证文案", "prompt": "基于用户好评生成转化文案"},
    ],
}


@router.get("/templates", summary="提示词模板列表")
async def list_templates(category: str = Query("")):
    if category and category in TEMPLATES:
        return ok({"templates": TEMPLATES[category]})
    return ok({"templates": TEMPLATES})


@router.get("/templates/{category}", summary="按分类获取模板")
async def get_templates(category: str):
    return ok({"templates": TEMPLATES.get(category, [])})
