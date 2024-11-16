import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi import Request

from app.models.api_key import ApiKey
from app.models.user import User

# These are actually needed - start
from app.models.base_model import BaseModel
from app.models.billing_credit import BillingCredit
from app.models.dataset import Dataset
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.usage import Usage
# These are actually needed - end

from app.core.authentication import (
    get_user_by_email,
    get_api_key,
    get_user_from_api_key,
    get_current_active_user,
    get_session_user
)
from app.core.constants import ApiKeyStatus, UserStatus
from app.core.exceptions import InvalidApiKeyError, InvalidUserSessionError


class MockDBResult:
    def __init__(self, return_value):
        self.return_value = return_value

    def scalar_one_or_none(self):
        return self.return_value


@pytest.fixture
def mock_db():
    """Create a mock database session with async execute."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_relationships():
    """Create empty mock relationships for the User model."""
    return {
        'datasets': [],
        'fine_tuning_jobs': [],
        'fine_tuned_models': [],
        'api_keys': [],
        'usage_records': [],
        'billing_credits': []
    }


@pytest.fixture
def mock_user(mock_relationships):
    """Create a mock user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        auth0_user_id="auth0|123",
        email_verified=True,
        status=UserStatus.ACTIVE,
        stripe_customer_id="cust_123"
    )
    # Set relationships
    for attr, value in mock_relationships.items():
        setattr(user, attr, value)
    return user


@pytest.fixture
def mock_inactive_user(mock_relationships):
    """Create a mock inactive user."""
    user = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        name="Inactive User",
        auth0_user_id="auth0|456",
        email_verified=True,
        status=UserStatus.INACTIVE,
        stripe_customer_id="cust_456"
    )
    # Set relationships
    for attr, value in mock_relationships.items():
        setattr(user, attr, value)
    return user


@pytest.fixture
def mock_api_key(mock_user):
    """Create a mock API key."""
    api_key_secret = "test_key_12345"
    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        name="test_key",
        prefix="test1234",
        key_hash="hashed_key",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=ApiKeyStatus.ACTIVE
    )
    # Set up the relationship
    api_key.user = mock_user
    mock_user.api_keys.append(api_key)
    return api_key, api_key_secret


@pytest.mark.asyncio
async def test_get_user_by_email_existing(mock_db, mock_user):
    """Test getting an existing user by email."""
    # Setup the mock to return a MockDBResult
    mock_db.execute.return_value = MockDBResult(mock_user)

    user = await get_user_by_email(mock_db, "test@example.com")
    assert user is mock_user
    assert user.email == "test@example.com"
    assert user.name == "Test User"


@pytest.mark.asyncio
async def test_get_user_by_email_nonexistent(mock_db):
    """Test getting a nonexistent user by email."""
    # Setup the mock to return None
    mock_db.execute.return_value = MockDBResult(None)

    user = await get_user_by_email(mock_db, "nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_get_api_key():
    """Test extracting API key from header."""
    api_key = await get_api_key("test_key")
    assert api_key == "test_key"


@pytest.mark.asyncio
async def test_get_api_key_none():
    """Test extracting API key when none is provided."""
    api_key = await get_api_key(None)
    assert api_key is None


@pytest.mark.asyncio
async def test_get_user_from_api_key_valid(mock_db, mock_user, mock_api_key):
    """Test getting user with valid API key."""
    api_key, api_key_secret = mock_api_key

    # Setup the mock to return a MockDBResult
    mock_db.execute.return_value = MockDBResult(api_key)

    with patch.object(ApiKey, 'verify_key', return_value=True):
        user = await get_user_from_api_key(mock_db, api_key_secret)
        assert user.id == mock_user.id
        assert user.email == mock_user.email


@pytest.mark.asyncio
async def test_get_user_from_api_key_invalid_key(mock_db):
    """Test getting user with invalid API key."""
    # Setup the mock to return None
    mock_db.execute.return_value = MockDBResult(None)

    with pytest.raises(InvalidApiKeyError):
        await get_user_from_api_key(mock_db, "invalid_key")


@pytest.mark.asyncio
async def test_get_user_from_api_key_verification_fails(mock_db, mock_api_key):
    """Test getting user with key that fails verification."""
    api_key, api_key_secret = mock_api_key

    # Setup the mock to return a MockDBResult
    mock_db.execute.return_value = MockDBResult(api_key)

    with patch.object(ApiKey, 'verify_key', return_value=False):
        with pytest.raises(InvalidApiKeyError):
            await get_user_from_api_key(mock_db, api_key_secret)


@pytest.mark.asyncio
async def test_get_session_user_valid(mock_db, mock_user):
    """Test getting user from valid session."""
    mock_request = MagicMock(spec=Request)
    mock_request.session = {"user": {"email": mock_user.email}}

    # Mock the database query
    mock_db.execute.return_value = MockDBResult(mock_user)

    user = await get_session_user(mock_request, mock_db)
    assert user.id == mock_user.id
    assert user.email == mock_user.email


@pytest.mark.asyncio
async def test_get_session_user_no_session(mock_db):
    """Test getting user with no session."""
    mock_request = MagicMock(spec=Request)
    mock_request.session = {}

    user = await get_session_user(mock_request, mock_db)
    assert user is None


@pytest.mark.asyncio
async def test_get_current_active_user_with_api_key(mock_db, mock_user, mock_api_key):
    """Test getting current user with valid API key."""
    api_key, api_key_secret = mock_api_key

    # Mock get_user_from_api_key to return the mock user
    async def mock_get_user(*args, **kwargs):
        return mock_user

    with patch('app.core.authentication.get_user_from_api_key', mock_get_user), \
            patch('app.core.authentication.create_stripe_customer', AsyncMock()) as mock_create_stripe:
        user = await get_current_active_user(None, api_key_secret, mock_db)
        assert user.id == mock_user.id
        assert user.email == mock_user.email
        mock_create_stripe.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_active_user_inactive_user(mock_db, mock_inactive_user):
    """Test getting current user with inactive user account."""
    # Mock get_session_user to return our inactive user
    async def mock_get_session_user(*args, **kwargs):
        return mock_inactive_user

    with patch('app.core.authentication.get_session_user', mock_get_session_user):
        with pytest.raises(InvalidUserSessionError):
            await get_current_active_user(mock_inactive_user, None, mock_db)


@pytest.mark.asyncio
async def test_get_current_active_user_inactive_via_api_key(mock_db, mock_inactive_user):
    """Test getting inactive user via API key."""
    # Mock get_user_from_api_key to return the inactive user
    async def mock_get_user(*args, **kwargs):
        return mock_inactive_user

    with patch('app.core.authentication.get_user_from_api_key', mock_get_user):
        with pytest.raises(InvalidUserSessionError):
            await get_current_active_user(None, "test_key", mock_db)


@pytest.mark.asyncio
async def test_get_session_user_inactive_user(mock_db, mock_inactive_user):
    """Test getting session user when user is inactive."""
    mock_request = MagicMock(spec=Request)
    mock_request.session = {"user": {"email": mock_inactive_user.email}}

    # Mock the database query
    mock_db.execute.return_value = MockDBResult(mock_inactive_user)

    user = await get_session_user(mock_request, mock_db)
    assert user is None  # should return None for inactive users


@pytest.mark.asyncio
async def test_get_user_from_api_key_inactive_user(mock_db, mock_inactive_user):
    """Test getting user with API key when user is inactive."""
    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=mock_inactive_user.id,
        name="test_key",
        prefix="test1234",
        key_hash="hashed_key",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=ApiKeyStatus.ACTIVE,
        user=mock_inactive_user
    )

    # Setup the mock to return a MockDBResult
    mock_db.execute.return_value = MockDBResult(api_key)

    with patch.object(ApiKey, 'verify_key', return_value=True):
        with pytest.raises(InvalidApiKeyError):
            await get_user_from_api_key(mock_db, "test_key_12345")
