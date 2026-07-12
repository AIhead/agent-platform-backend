# Agent Platform Backend

AI 智能体平台后端，FastAPI + DeepSeek + SQLite（默认）/ PostgreSQL。

## 技术栈

- Python FastAPI + SQLAlchemy 2.0
- SQLite（默认）/ PostgreSQL + pgvector（可选，用于 RAG）
- DeepSeek API（SSE 流式）
- BGE 本地向量化

## 快速启动

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
python seed_data.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 数据库

| 数据库 | 适用场景 |
|------|------|
| SQLite（默认） | 快速部署，无需额外安装 |
| PostgreSQL + pgvector | 本地开发，支持知识库 RAG 向量检索 |

切换方式：修改 DATABASE_URL 即可。

## 部署

```bash
# 生产部署（systemd）
cp deploy/agent-backend.service /etc/systemd/system/
systemctl enable --now agent-backend
```

## API 文档

| 文档 | 地址 |
|------|------|
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
