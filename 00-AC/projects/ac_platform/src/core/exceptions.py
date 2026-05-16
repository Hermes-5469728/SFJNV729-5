"""统一异常处理 · src/core/exceptions.py"""
from fastapi import Request
from fastapi.responses import JSONResponse


class ACException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"


class NotFoundError(ACException):
    status_code = 404
    detail = "Resource not found"


class ValidationError(ACException):
    status_code = 422
    detail = "Validation failed"


class ForbiddenError(ACException):
    status_code = 403
    detail = "Forbidden"


class UnauthorizedError(ACException):
    status_code = 401
    detail = "Unauthorized"


async def ac_exception_handler(request: Request, exc: ACException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


def register_exceptions(app):
    app.add_exception_handler(ACException, ac_exception_handler)
    app.add_exception_handler(NotFoundError, ac_exception_handler)
    app.add_exception_handler(ValidationError, ac_exception_handler)
    app.add_exception_handler(ForbiddenError, ac_exception_handler)
    app.add_exception_handler(UnauthorizedError, ac_exception_handler)
