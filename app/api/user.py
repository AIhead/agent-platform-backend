from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import ok
from app.models.user import User

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", summary="用户资料")
async def get_profile(user: User = Depends(get_current_user)):
    return ok({
        "id": user.id,
        "account": user.account or user.phone,
        "nickname": user.nickname,
        "avatar": user.avatar_url or "",
    })
