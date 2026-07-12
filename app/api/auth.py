from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.core.response import ok, fail, ErrorCode
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", summary="注册")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    exist = await db.execute(select(User).where(User.account == req.account))
    if exist.scalar_one_or_none():
        return fail(ErrorCode.ACCOUNT_EXISTS, "账号已存在")

    user = User(
        phone=req.account,
        account=req.account,
        password_hash=hash_password(req.password),
        nickname=req.account,
        avatar_url="https://mmbiz.qpic.cn/sz_mmbiz_jpg/w4bIWyNFlcic9K5kMfM9sSxFzaUuapvk6K1SfEwOKJkgxsbicW57v5GQHq7VOzvTI6vXMETsNg6lUiaz8NYEhWGlQ/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=13",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id)
    return ok({"token": token, "user": _user_info(user)})


@router.post("/login", summary="账号密码登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(or_(User.account == req.account, User.phone == req.account))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        return fail(ErrorCode.ACCOUNT_OR_PASSWORD_ERROR, "账号或密码错误")

    token = create_access_token(user.id)
    return ok({"token": token, "user": _user_info(user)})


@router.get("/me", summary="获取当前用户信息")
async def get_me(user: User = Depends(get_current_user)):
    return ok(_user_info(user))


def _user_info(user: User) -> dict:
    return {
        "id": user.id,
        "account": user.account or user.phone,
        "nickname": user.nickname,
        "avatar": user.avatar_url or "",
        "isMember": user.is_member,
        "memberExpireAt": int(user.member_expire_at.timestamp() * 1000) if user.member_expire_at else None,
    }
