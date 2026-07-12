from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.response import ErrorCode
from app.api import auth, agents, conversations, knowledge, user, prompts, member

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI 智能体平台 API",
    description="多智能体协作平台 API 文档",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(knowledge.router)
app.include_router(user.router)
app.include_router(prompts.router)
app.include_router(member.router)


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(status_code=401, content={"code": ErrorCode.NOT_LOGIN, "msg": "未登录", "data": None})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"code": ErrorCode.NOT_FOUND, "msg": "资源不存在", "data": None})

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"code": ErrorCode.SERVER_ERROR, "msg": "服务异常", "data": None})


@app.get("/api/health", summary="健康检查", tags=["系统"])
async def health():
    from app.core.response import ok
    return ok({"status": "ok"})
