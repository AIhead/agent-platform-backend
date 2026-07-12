from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.core.response import ok
from app.models.user import User

router = APIRouter(prefix="/api/member", tags=["member"])


@router.get("/status", summary="会员状态")
async def member_status(user: User = Depends(get_current_user)):
    return ok({
        "isMember": user.is_member,
        "memberExpireAt": int(user.member_expire_at.timestamp() * 1000) if user.member_expire_at else None,
    })
