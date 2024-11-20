import json
import logging

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import Headers

from app.core.exceptions import (
    AppException,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ServerError,
    PaymentNeededError,
    InvalidApiKeyError,
    InvalidUserSessionError,
    UserNotFoundError,
    EmailAlreadyExistsError,
    ApiKeyAlreadyExistsError,
    ApiKeyNotFoundError,
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
    BaseModelNotFoundError,
    FineTunedModelNotFoundError,
    FineTuningJobNotFoundError,
    FineTuningJobAlreadyExistsError,
    FineTuningJobCreationError,
    FineTuningJobRefreshError,
    FineTuningJobCancellationError,
    StripeCheckoutSessionCreationError,
    StorageError,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler
)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return logging.getLogger("test_logger")

@pytest.fixture
def mock_request():
    """Create a mock request for testing handlers."""
    async def mock_body():
        return b""

    return Request({
        'type': 'http',
        'method': 'GET',
        'headers': Headers({}),
        'path': '/',
    })

def test_app_exception_base():
    """Test base AppException functionality."""
    exc = AppException(status_code=400, detail="Test error")
    assert exc.status_code == 400
    assert exc.detail == "Test error"
    assert str(exc) == "Test error"

def test_exception_logging(mock_logger):
    """Test exception logging functionality."""
    exc = AppException(status_code=400, detail="Test error", logger=mock_logger)
    assert exc.status_code == 400

    # Test logging at different levels
    error_exc = ServerError("Server error", mock_logger)
    assert error_exc.status_code == 500

    warning_exc = BadRequestError("Bad request", mock_logger)
    assert warning_exc.status_code == 422

def test_specific_exceptions(mock_logger):
    """Test all specific exception types."""
    exceptions = [
        (NotFoundError, 404, "Not found"),
        (UnauthorizedError, 401, "Unauthorized"),
        (ForbiddenError, 403, "Forbidden"),
        (BadRequestError, 422, "Bad request"),
        (ServerError, 500, "Server error"),
        (PaymentNeededError, 402, "Payment needed"),
        (InvalidApiKeyError, 401, "Invalid API key"),
        (InvalidUserSessionError, 401, "Invalid session"),
        (UserNotFoundError, 404, "User not found"),
        (EmailAlreadyExistsError, 422, "Email exists"),
        (ApiKeyAlreadyExistsError, 422, "API key exists"),
        (ApiKeyNotFoundError, 404, "API key not found"),
        (DatasetAlreadyExistsError, 422, "Dataset exists"),
        (DatasetNotFoundError, 404, "Dataset not found"),
        (BaseModelNotFoundError, 404, "Base model not found"),
        (FineTunedModelNotFoundError, 404, "Fine-tuned model not found"),
        (FineTuningJobNotFoundError, 404, "Job not found"),
        (FineTuningJobAlreadyExistsError, 422, "Job exists"),
        (FineTuningJobCreationError, 500, "Job creation failed"),
        (FineTuningJobRefreshError, 500, "Job refresh failed"),
        (FineTuningJobCancellationError, 500, "Job cancellation failed"),
        (StripeCheckoutSessionCreationError, 500, "Stripe session failed"),
        (StorageError, 500, "Storage error"),
    ]

    for exc_class, status_code, detail in exceptions:
        exc = exc_class(detail, mock_logger)
        assert exc.status_code == status_code
        assert exc.detail == detail

@pytest.mark.asyncio
async def test_app_exception_handler(mock_request):
    """Test app exception handler."""
    exc = BadRequestError("Test error")
    response = await app_exception_handler(mock_request, exc)

    assert response.status_code == 422
    content = json.loads(response.body)
    assert content["status"] == 422
    assert content["message"] == "Test error"

@pytest.mark.asyncio
async def test_validation_exception_handler(mock_request):
    """Test validation exception handler."""
    exc = RequestValidationError(errors=[{"loc": ("body", "field"), "msg": "Invalid value"}])
    response = await validation_exception_handler(mock_request, exc)

    assert response.status_code == 422
    content = json.loads(response.body)
    assert content["status"] == 422
    assert isinstance(content["message"], list)

@pytest.mark.asyncio
async def test_sqlalchemy_exception_handler(mock_request):
    """Test SQLAlchemy exception handler."""
    exc = SQLAlchemyError("Database error")
    response = await sqlalchemy_exception_handler(mock_request, exc)

    assert response.status_code == 500
    content = json.loads(response.body)
    assert content["status"] == 500
    assert "unexpected database error" in content["message"].lower()

@pytest.mark.asyncio
async def test_generic_exception_handler(mock_request):
    """Test generic exception handler."""
    exc = Exception("Unexpected error")
    response = await generic_exception_handler(mock_request, exc)

    assert response.status_code == 500
    content = json.loads(response.body)
    assert content["status"] == 500
    assert "unexpected error" in content["message"].lower()

def test_exception_inheritance():
    """Test exception inheritance hierarchy."""
    # Test that all custom exceptions inherit from AppException
    exceptions = [
        NotFoundError,
        UnauthorizedError,
        ForbiddenError,
        BadRequestError,
        ServerError,
        PaymentNeededError,
        InvalidApiKeyError,
        InvalidUserSessionError,
        UserNotFoundError,
        EmailAlreadyExistsError,
        ApiKeyAlreadyExistsError,
        ApiKeyNotFoundError,
        DatasetAlreadyExistsError,
        DatasetNotFoundError,
        BaseModelNotFoundError,
        FineTunedModelNotFoundError,
        FineTuningJobNotFoundError,
        FineTuningJobAlreadyExistsError,
        FineTuningJobCreationError,
        FineTuningJobRefreshError,
        FineTuningJobCancellationError,
        StripeCheckoutSessionCreationError,
        StorageError,
    ]

    for exc_class in exceptions:
        assert issubclass(exc_class, AppException)

def test_exception_attributes():
    """Test exception attributes preservation."""
    exc = AppException(status_code=400, detail="Test error")

    # Test that exception attributes are preserved when caught
    try:
        raise exc
    except AppException as caught_exc:
        assert caught_exc.status_code == 400
        assert caught_exc.detail == "Test error"
        assert str(caught_exc) == "Test error"