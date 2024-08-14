from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


# Core exceptions


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class UserNotFoundError(NotFoundError):
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail)


class InvalidTokenError(UnauthorizedError):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail)


class ExpiredTokenError(UnauthorizedError):
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail)


class EmailAlreadyExistsError(BadRequestError):
    def __init__(self, detail: str = "Email already registered"):
        super().__init__(detail)


# API exceptions


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected database error occurred"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
