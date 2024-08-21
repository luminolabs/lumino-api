import logging
from logging import Logger

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


# Core exceptions


class AppException(HTTPException):
    """Base exception for application-specific errors."""
    def __init__(self, status_code: int, detail: str, logger: Logger):
        """
        Initialize the exception.

        Args:
            status_code (int): The HTTP status code.
            detail (str): The detail message.
            logger (Logger): The logger instance to use.
        """
        super().__init__(status_code=status_code, detail=detail)
        # We'd like to log all exceptions, so we'll log them here in the base class
        self.log(logger)

    def log(self, logger: Logger):
        """
        Log the exception using the provided logger.

        Args:
            logger (Logger): The logger instance to use.
        """
        level = None
        if self.status_code >= 500:
            level = logging.ERROR
        elif self.status_code >= 400:
            level = logging.WARNING
        if level:
            logger.log(level, self.detail)


    def __str__(self) -> str:
        """
        Used to return the exception message when the exception is cast to a string.

        The original __str__ method returns both status code and message.
        We're overriding it to return only the message, so that when
        multiple exceptions are raised in a single request, and messages are concatenated,
        the response body remains clean.

        The status code is still available in the response headers and the response JSON.

        Returns:
            str: The detail message of the exception.
        """
        return self.detail


class NotFoundError(AppException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(status_code=404, detail=detail, logger=logger)


class UnauthorizedError(AppException):
    """Exception raised when authentication fails."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(status_code=401, detail=detail, logger=logger)


class ForbiddenError(AppException):
    """Exception raised when a user doesn't have permission to access a resource."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(status_code=403, detail=detail, logger=logger)


class BadRequestError(AppException):
    """Exception raised when the request is malformed or invalid."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(status_code=422, detail=detail, logger=logger)


class ServerError(AppException):
    """Exception raised when an unexpected application error occurs."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(status_code=500, detail=detail, logger=logger)


# Authentication exceptions


class InvalidApiKeyError(UnauthorizedError):
    """Exception raised when an invalid API key is provided."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class InvalidBearerTokenError(UnauthorizedError):
    """Exception raised when an invalid token is provided."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# User exceptions


class UserNotFoundError(NotFoundError):
    """Exception raised when a requested user is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class EmailAlreadyExistsError(BadRequestError):
    """Exception raised when attempting to register with an email that's already in use."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# API key exceptions


class ApiKeyAlreadyExistsError(BadRequestError):
    """Exception raised when there's an error creating an API key."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class ApiKeyNotFoundError(NotFoundError):
    """Exception raised when a requested API key is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# Dataset exceptions


class DatasetCreationError(BadRequestError):
    """Exception raised when there's an error creating a dataset."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class DatasetNotFoundError(NotFoundError):
    """Exception raised when a requested dataset is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class DatasetUpdateError(BadRequestError):
    """Exception raised when there's an error updating a dataset."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class DatasetDeletionError(BadRequestError):
    """Exception raised when there's an error deleting a dataset."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# Storage exceptions


class StorageError(AppException):
    """Exception raised when there's an error with storage operations."""
    def __init__(self, detail: str = "Storage operation failed"):
        super().__init__(status_code=500, detail=detail)


# Model exceptions


class BaseModelNotFoundError(NotFoundError):
    """Exception raised when a requested base model is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class FineTunedModelNotFoundError(NotFoundError):
    """Exception raised when a requested fine-tuned model is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


class ModelRetrievalError(BadRequestError):
    """Exception raised when there's an error retrieving models."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# Fine-Tuning exceptions


class FineTuningJobCreationError(BadRequestError):
    """Exception raised when there's an error creating a fine-tuning job."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)

class FineTuningJobNotFoundError(NotFoundError):
    """Exception raised when a requested fine-tuning job is not found."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)

class FineTuningJobCancelError(BadRequestError):
    """Exception raised when there's an error cancelling a fine-tuning job."""
    def __init__(self, detail: str, logger: Logger):
        super().__init__(detail, logger)


# Exception handlers


async def app_exception_handler(request: Request, exc: AppException):
    """Handler for application-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": exc.status_code, "message": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    return JSONResponse(
        status_code=422,
        content={"status": 422, "message": exc.errors()},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler for SQLAlchemy database errors."""
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "An unexpected database error occurred"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler for generic, uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "An unexpected error occurred"},
    )
