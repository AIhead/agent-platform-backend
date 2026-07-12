# Agent Platform Backend

AI 智能体平台后端，基于 FastAPI + DeepSeek + PostgreSQL + pgvector。

## 技术栈

- **框架**：Python FastAPI
- **ORM**：SQLAlchemy 2.0（异步）
- **数据库**：PostgreSQL 16 + pgvector（向量检索）
- **AI**：DeepSeek API（SSE 流式对话）
- **向量化**：BAAI/bge-small-zh-v1.5（本地，512 维）

## 快速启动

### 前置条件
- Python 3.10+
- PostgreSQL 16+ + pgvector 扩展

### 安装
```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 DEEPSEEK_API_KEY
python seed_data.py     # 初始化智能体数据
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API 文档
| 文档 | 地址 |
|------|------|
| Swagger（交互测试） | http://localhost:8000/docs |
| ReDoc（阅读） | http://localhost:8000/redoc |

## 项目结构

```
app/
├── api/              # 路由层（7 个模块）
│   ├── auth.py       # 认证（注册/登录）
│   ├── agents.py     # 智能体（列表/详情/配置）
│   ├── conversations.py  # 会话 + SSE 流式消息
│   ├── knowledge.py  # 知识库（上传/搜索/删除）
│   ├── member.py     # 会员状态
│   ├── prompts.py    # 提示词模板
│   └── user.py       # 用户资料
├── core/             # 基础设施
│   ├── config.py     # 环境变量配置
│   ├── security.py   # JWT + bcrypt
│   ├── database.py   # SQLAlchemy 异步引擎
│   ├── deps.py       # 依赖注入（认证中间件）
│   └── response.py   # 统一响应 {code, msg, data}
├── models/           # 数据库模型（6 张表）
├── services/         # 业务逻辑
│   ├── agent_service.py  # Prompt 模板引擎
│   ├── llm_service.py    # DeepSeek + BGE
│   ├── rag_service.py    # 知识库检索
│   └── file_service.py   # 文件处理
└── main.py           # 入口
```

## API 接口（18 个端点）

所有接口统一 `{code, msg, data}` 格式。

| 模块 | 端点 | 说明 |
|------|------|------|
| auth | POST /api/auth/register | 注册 |
| auth | POST /api/auth/login | 登录 |
| auth | GET /api/auth/me | 当前用户 |
| agents | GET /api/agents | 智能体列表 |
| agents | GET /api/agents/{id} | 智能体详情 |
| agents | GET /api/agents/{id}/config | 智能体配置 |
| conversations | POST /api/conversations | 创建对话 |
| conversations | GET /api/conversations | 对话列表 |
| conversations | GET /api/conversations/{id} | 对话消息 |
| chat | POST /api/chat/messages | 发送消息（SSE） |
| knowledge | GET /api/knowledge | 文档列表 |
| knowledge | POST /api/knowledge/upload | 上传文档 |
| knowledge | POST /api/knowledge/search | 全文搜索 |
| knowledge | POST /api/knowledge/batch-delete | 批量删除 |
| knowledge | DELETE /api/knowledge/{id} | 删除文档 |
| member | GET /api/member/status | 会员状态 |
| prompts | GET /api/prompts/templates | 模板列表 |
| user | GET /api/user/profile | 用户资料 |

## 智能体

| ID | 名称 | 子功能 |
|------|------|--------|
| 728c6cdd-... | 商业咨询导师 | 商业定位/产品矩阵/内容操盘手 |
| b5c0c88e-... | 获客高手 | 短视频文案/直播策略/直播脚本 |
| 4bfa5a81-... | 成交转化 | 朋友圈文案 |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| DEEPSEEK_API_KEY | 是 | DeepSeek API Key |
| DATABASE_URL | 否 | 数据库连接字符串 |
| DEBUG | 否 | 调试模式（默认 true） |
