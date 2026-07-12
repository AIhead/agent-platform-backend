"""Unified response wrapper matching frontend contract."""
from typing import Any, Optional

from fastapi.responses import JSONResponse


class ErrorCode:
    SUCCESS = 0
    PARAM_ERROR = 40001
    ACCOUNT_OR_PASSWORD_ERROR = 40002
    ACCOUNT_EXISTS = 40003
    NOT_LOGIN = 40101
    LOGIN_EXPIRED = 40102
    NO_PERMISSION = 40301
    NOT_FOUND = 40401
    SERVER_ERROR = 50000


def ok(data: Any = None, msg: str = "ok") -> JSONResponse:
    return JSONResponse(content={"code": ErrorCode.SUCCESS, "msg": msg, "data": data})


def fail(code: int, msg: str, data: Any = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content={"code": code, "msg": msg, "data": data}, status_code=status_code)
