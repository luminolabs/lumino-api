from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


# Core exceptions


class AppException(HTTPException):
    """Base exception for application-specific errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(AppException):
    """Exception raised when authentication fails."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(AppException):
    """Exception raised when a user doesn't have permission to access a resource."""
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(AppException):
    """Exception raised when the request is malformed or invalid."""
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


# User exceptions


class UserNotFoundError(NotFoundError):
    """Exception raised when a requested user is not found."""
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail)


class InvalidTokenError(UnauthorizedError):
    """Exception raised when an invalid token is provided."""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail)


class ExpiredTokenError(UnauthorizedError):
    """Exception raised when an expired token is provided."""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail)


class EmailAlreadyExistsError(BadRequestError):
    """Exception raised when attempting to register with an email that's already in use."""
    def __init__(self, detail: str = "Email already registered"):
        super().__init__(detail)


# API key exceptions


class ApiKeyCreationError(BadRequestError):
    """Exception raised when there's an error creating an API key."""
    def __init__(self, detail: str = "Failed to create API key"):
        super().__init__(detail)


class ApiKeyNotFoundError(NotFoundError):
    """Exception raised when a requested API key is not found."""
    def __init__(self, detail: str = "API key not found"):
        super().__init__(detail)


class ApiKeyUpdateError(BadRequestError):
    """Exception raised when there's an error updating an API key."""
    def __init__(self, detail: str = "Failed to update API key"):
        super().__init__(detail)


class ApiKeyRevocationError(BadRequestError):
    """Exception raised when there's an error revoking an API key."""
    def __init__(self, detail: str = "Failed to revoke API key"):
        super().__init__(detail)


# Dataset exceptions


class DatasetCreationError(BadRequestError):
    """Exception raised when there's an error creating a dataset."""
    def __init__(self, detail: str = "Failed to create dataset"):
        super().__init__(detail)


class DatasetNotFoundError(NotFoundError):
    """Exception raised when a requested dataset is not found."""
    def __init__(self, detail: str = "Dataset not found"):
        super().__init__(detail)


class DatasetUpdateError(BadRequestError):
    """Exception raised when there's an error updating a dataset."""
    def __init__(self, detail: str = "Failed to update dataset"):
        super().__init__(detail)


class DatasetDeletionError(BadRequestError):
    """Exception raised when there's an error deleting a dataset."""
    def __init__(self, detail: str = "Failed to delete dataset"):
        super().__init__(detail)


# Storage exceptions

class StorageError(AppException):
    """Exception raised when there's an error with storage operations."""
    def __init__(self, detail: str = "Storage operation failed"):
        super().__init__(status_code=500, detail=detail)


# Exception handlers


async def app_exception_handler(request: Request, exc: AppException):
    """Handler for application-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler for SQLAlchemy database errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected database error occurred"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler for generic, uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )