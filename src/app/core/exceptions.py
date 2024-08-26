import logging
from logging import Logger
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config_manager import config
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


class AppException(HTTPException):
    """Base exception for application-specific errors."""
    def __init__(self, status_code: int, detail: str, logger: Optional[Logger] = None):
        """
        Initialize the exception.

        Args:
            status_code (int): The HTTP status code.
            detail (str): The detail message.
            logger (Optional[Logger]): The logger instance to use, if any.
        """
        super().__init__(status_code=status_code, detail=detail)
        if logger:
            self.log(logger)

    def log(self, logger: Logger):
        """
        Log the exception using the provided logger.

        Args:
            logger (Logger): The logger instance to use.
        """
        level = logging.ERROR if self.status_code >= 500 else logging.WARNING
        logger.log(level, self.detail)

    def __str__(self) -> str:
        """
        Return the exception message when cast to a string.

        Returns:
            str: The detail message of the exception.
        """
        return self.detail


class NotFoundError(AppException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(status_code=404, detail=detail, logger=logger)


class UnauthorizedError(AppException):
    """Exception raised when authentication fails."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(status_code=401, detail=detail, logger=logger)


class ForbiddenError(AppException):
    """Exception raised when a user doesn't have permission to access a resource."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(status_code=403, detail=detail, logger=logger)


class BadRequestError(AppException):
    """Exception raised when the request is malformed or invalid."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(status_code=422, detail=detail, logger=logger)


class ServerError(AppException):
    """Exception raised when an unexpected application error occurs."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(status_code=500, detail=detail, logger=logger)


# Authentication exceptions


class InvalidApiKeyError(UnauthorizedError):
    """Exception raised when an invalid API key is provided."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class InvalidBearerTokenError(UnauthorizedError):
    """Exception raised when an invalid token is provided."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


# User exceptions


class UserNotFoundError(NotFoundError):
    """Exception raised when a requested user is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class EmailAlreadyExistsError(BadRequestError):
    """Exception raised when attempting to register with an email that's already in use."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


# API key exceptions


class ApiKeyAlreadyExistsError(BadRequestError):
    """Exception raised when there's an error creating an API key."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class ApiKeyNotFoundError(NotFoundError):
    """Exception raised when a requested API key is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


# Dataset exceptions


class DatasetAlreadyExistsError(BadRequestError):
    """Exception raised when there's an error creating a dataset."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class DatasetNotFoundError(NotFoundError):
    """Exception raised when a requested dataset is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


# Model exceptions


class BaseModelNotFoundError(NotFoundError):
    """Exception raised when a requested base model is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class FineTunedModelNotFoundError(NotFoundError):
    """Exception raised when a requested fine-tuned model is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


# Fine-Tuning exceptions


class FineTuningJobNotFoundError(NotFoundError):
    """Exception raised when a requested fine-tuning job is not found."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class FineTuningJobAlreadyExistsError(BadRequestError):
    """Exception raised when a fine-tuning job with the same name already exists."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class FineTuningJobCreationError(ServerError):
    """Exception raised when there's an error creating a fine-tuning job."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class FineTuningJobRefreshError(ServerError):
    """Exception raised when there's an error refreshing fine-tuning job details."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
        super().__init__(detail, logger)


class FineTuningJobCancellationError(ServerError):
    """Exception raised when there's an error stopping a fine-tuning job."""
    def __init__(self, detail: str, logger: Optional[Logger] = None):
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
    logger.exception(f"An unexpected database error occurred: {exc}, {exc.with_traceback(exc.__traceback__)}")
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "An unexpected database error occurred"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler for generic, uncaught exceptions."""
    logger.exception(f"An unexpected error occurred: {exc}, {exc.with_traceback(exc.__traceback__)}")
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "An unexpected error occurred"},
    )
