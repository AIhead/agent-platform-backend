from __future__ import annotations
from typing import AsyncGenerator
from string import Formatter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent
from app.services.llm_service import chat_completion_stream
from app.services.rag_service import retrieve_relevant_chunks


# Computed fields derived from user params (not in input_schema_json)
# Sub-function detail prompts — injected when user picks a sub_function
SUB_FUNCTION_PROMPTS = {
    # ===== 商业咨询导师 =====
    "商业定位咨询": (
        "## 任务：商业定位诊断\n"
        "1. 目标市场与用户画像\n2. 核心竞争力与差异化\n"
        "3. 商业模式建议（盈利模式/定价/LTV）\n4. 阶段性发展建议（0-1/1-10/风险）\n"
        "输出：结构化报告。"
    ),
    "产品矩阵设计": (
        "## 任务：产品矩阵设计\n"
        "1. 引流品设计 2. 利润品设计与功能分层\n"
        "3. 产品矩阵协同与转化路径 4. 产品路线图（MVP→V1→V2→V3）\n"
        "输出：可执行的产品方案。"
    ),
    "超级内容操盘手": (
        "## 任务：内容营销体系搭建\n"
        "1. 内容定位与选题矩阵 2. 内容生产SOP与AI提效\n"
        "3. 多平台分发策略（抖音/视频号/小红书/公众号）\n4. 效果评估与A/B测试\n"
        "输出：可执行的内容营销方案，附选题示例。"
    ),
    # ===== 获客高手 =====
    "短视频文案": (
        "## 任务：短视频文案生成\n"
        "请生成完整短视频内容：\n"
        "1. **【标题】**：1-2个备选\n"
        "2. **【文案正文】**：{content_type}格式，约{word_count}字\n"
        "3. **【画面建议】**：每段镜头建议\n"
        "4. **【BGM推荐】**\n\n"
        "要求：{tone_desc}、开头3秒钩子、节奏紧凑、{add_interaction_msg}。"
    ),
    "直播获客策略": (
        "## 任务：直播获客策略\n"
        "根据用户的人设和业务，给出直播获客策略：\n"
        "1. 直播人设定位与话术风格\n"
        "2. 单场直播节奏安排\n"
        "3. 引流与转化策略\n"
        "输出：完整的直播获客方案。"
    ),
    "直播脚本": (
        "## 任务：直播脚本\n"
        "生成开场/产品介绍/收尾核心环节完整脚本：\n"
        "1. 开场脚本 — 破冰、建立信任、预告福利\n"
        "2. 产品介绍脚本 — 痛点→解决方案→产品演示\n"
        "3. 收尾脚本 — 限时优惠、逼单话术、下期预告\n"
        "输出：可直接使用的完整直播脚本。"
    ),
    # ===== 成交转化 =====
    "朋友圈文案": (
        "你是一个朋友圈文案生成器。必须严格按照以下四点输出，缺一不可：\n"
        "1. 文案正文（场景：{scene}，每行≤20字，加emoji，适配换行，≤200字）\n"
        "2. 配图建议（推荐产品图/风景/生活照/表情包并说明理由）\n"
        "3. 发布时间建议（推荐最佳时间段并说明原因）\n"
        "4. 转化话术（1-2条评论区跟进话术）\n"
        "格式：用数字1.2.3.4.标记每个部分。"
    ),
    "社群成交": (
        "## 任务：社群成交方案\n"
        "1. 社群定位与日常运营节奏\n2. 互动开场脚本\n"
        "3. 干货内容脚本\n4. 成交转化脚本（产品+限时+逼单）\n"
        "输出：完整社群成交方案。"
    ),
    "私域直播成交": (
        "## 任务：私域直播成交\n"
        "根据人设和业务提供直播转化的策略：\n"
        "1. 直播转化策略\n"
        "2. 几天的直播内容：开场/干货/产品介绍/收尾核心环节完整脚本\n"
        "输出：完整的直播成交方案和脚本。"
    ),
    "社群成交": (
        "## 任务：社群成交\n"
        "根据人设和业务提供社群成交转化的策略：\n"
        "1. 社群成交策略\n"
        "2. 社群脚本内容：互动开场/干货内容/产品介绍/收尾核心环节完整脚本\n"
        "输出：完整的社群成交方案和脚本。"
    ),
    "沙龙会销": (
        "## 任务：沙龙/会销成交\n"
        "根据人设和业务提供会销成交转化的营销策略：\n"
        "1. 会销策略\n"
        "2. 线下会销内容：签到暖场/价值塑造/产品演示/成交收尾\n"
        "输出：可落地的会销执行方案。"
    ),
}

# Computed message for interaction toggle
def _compute_interaction_msg(params: dict) -> str:
    if params.get("add_interaction"):
        return "结尾必须加互动引导（点赞/评论/关注）"
    return "结尾自然收尾，不加营销引导语"


def _compute_derived_params(params: dict) -> dict:
    """Compute derived prompt variables from user-supplied params."""
    derived = {}

    # sub_function_prompt: detailed instructions based on user's sub_function choice
    if "sub_function" in params and params["sub_function"] in SUB_FUNCTION_PROMPTS:
        derived["sub_function_prompt"] = SUB_FUNCTION_PROMPTS[params["sub_function"]]

    # style_desc: human-readable style description
    style_map = {
        "爆款吸睛": "节奏快、情绪强烈，制造紧迫感",
        "干货科普": "理性分析、数据支撑，建立信任感",
        "悬念引导": "开头抛问题、层层递进再揭晓答案",
        "幽默风趣": "轻松有趣、网络化表达",
    }
    if "style" in params and params["style"] in style_map:
        derived["style_desc"] = style_map[params["style"]]

    # platform_rules: platform-specific constraints
    platform_rules_map = {
        "抖音": "- 标题不超过 30 字\n- 前 3 秒必须有视觉/听觉爆点\n- 多用「老板」「家人们」等亲切称呼\n- 结尾引导点赞评论关注三连",
        "视频号": "- 标题偏稳重，可用设问句\n- 内容适合 40+ 人群口味\n- 鼓励转发到朋友圈\n- 结尾引导点亮小红心和关注",
        "小红书": "- 标题多 emoji、多换行\n- 口播稿同步作为笔记正文\n- 语气要像闺蜜/姐妹分享\n- 标签 # 关键词放在末尾",
        "快手": "- 标题接地气、口语化\n- 内容真实、贴近生活\n- 强调「老铁」「家人们」等圈层文化\n- 结尾引导双击加关注",
    }
    if "platform" in params and params["platform"] in platform_rules_map:
        derived["platform_rules"] = platform_rules_map[params["platform"]]

    # tone description
    tone_map = {
        "活泼": "语气活泼有趣，用轻松的语言表达",
        "严肃": "语气正式严肃，用专业的语言表达",
        "专业": "语气专业权威，用精准的语言表达",
    }
    if "tone" in params and params["tone"] in tone_map:
        derived["tone_desc"] = tone_map[params["tone"]]

    # word count: duration * 3
    if "duration" in params:
        try:
            derived["word_count"] = int(params["duration"]) * 3
        except (ValueError, TypeError):
            derived["word_count"] = 180

    # interaction message
    derived["add_interaction_msg"] = _compute_interaction_msg(params)

    return derived


def build_user_message(params: dict, user_message: str) -> str:
    """Build the final user message from structured params and free-text input."""
    parts = []
    # Only include user-facing params (skip "add_interaction" etc. from display)
    display_params = {k: v for k, v in params.items() if k not in ("add_interaction",)}
    if display_params:
        param_lines = [f"- **{key}**：{value}" for key, value in display_params.items()]
        parts.append("## 参数设置\n" + "\n".join(param_lines))
    if user_message:
        parts.append(f"## 需求描述\n{user_message}")
    if not parts:
        parts.append("请开始你的分析。")
    return "\n\n".join(parts)


def fill_prompt_template(template: str, params: dict) -> str:
    """Two-pass expansion: first {sub_function_prompt}, then all remaining params."""
    merged = {**params, **_compute_derived_params(params)}

    class SafeDict(dict):
        def __missing__(self, key):
            return f"{{{key}}}"

    # Pass 1: expand only {sub_function_prompt} into the template
    values1 = SafeDict()
    if "sub_function_prompt" in merged:
        values1["sub_function_prompt"] = merged["sub_function_prompt"]
    # Add sub_function itself
    if "sub_function" in params:
        values1["sub_function"] = params["sub_function"]
    result = template.format_map(values1)

    # Pass 2: expand remaining placeholders in the result
    values2 = SafeDict()
    for f in {f[1] for f in Formatter().parse(result) if f[1] is not None}:
        values2[f] = merged.get(f, "")
    return result.format_map(values2)


async def run_agent_stream(
    db: AsyncSession,
    agent_id: str,
    params: dict,
    user_message: str,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Execute an agent and yield streaming response chunks."""
    # 1. Load agent definition
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        yield "错误：智能体不存在"
        return

    # 2. Build system prompt from template
    system_prompt = fill_prompt_template(agent.system_prompt, params)

    # 3. Inject RAG context (knowledge base retrieval)
    rag_context = await retrieve_relevant_chunks(db, user_message, user_id)
    if rag_context:
        system_prompt += f"\n\n## 参考知识库\n{rag_context}"

    # 4. Build user message
    full_user_message = build_user_message(params, user_message)

    # 5. Stream from LLM
    async for chunk in chat_completion_stream(
        system_prompt=system_prompt,
        user_message=full_user_message,
    ):
        yield chunk
