from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from app.core.authentication import (
    get_api_key,
    get_user_from_api_key,
    get_session_user,
    get_current_active_user,
    admin_required
)
from app.core.constants import UserStatus, ApiKeyStatus
from app.core.exceptions import (
    InvalidApiKeyError,
    UnauthorizedError,
    ForbiddenError
)
from app.models.api_key import ApiKey
from app.models.user import User
from app.queries.common import now_utc, make_naive


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.status = UserStatus.ACTIVE
    user.is_admin = False
    user.stripe_customer_id = "cus_123"
    return user


@pytest.fixture
def mock_api_key():
    """Create a mock API key object."""
    api_key = MagicMock(spec=ApiKey)
    api_key.user_id = "test-user-id"
    api_key.prefix = "test1234"
    api_key.status = ApiKeyStatus.ACTIVE
    api_key.expires_at = make_naive(now_utc() + timedelta(days=1))
    api_key.verify_key.return_value = True
    return api_key


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock(spec=Request)
    request.session = {}
    return request


@pytest.mark.asyncio
async def test_get_api_key():
    """Test getting API key from header."""
    # Test with API key present
    api_key = await get_api_key(x_api_key="test-key")
    assert api_key == "test-key"

    # Test with no API key
    api_key = await get_api_key(x_api_key=None)
    assert api_key is None


@pytest.mark.asyncio
async def test_get_user_from_api_key(mock_db, mock_user, mock_api_key):
    """Test getting user from API key."""
    # Set up mocks
    with patch('app.core.authentication.api_key_queries') as mock_api_key_queries, \
            patch('app.core.authentication.user_queries') as mock_user_queries:
        # Make query functions async
        mock_api_key_queries.get_api_key_by_prefix = AsyncMock(return_value=mock_api_key)
        mock_user_queries.get_user_by_id = AsyncMock(return_value=mock_user)

        # Test valid API key
        user = await get_user_from_api_key(mock_db, "test-api-key")
        assert user == mock_user
        mock_api_key_queries.get_api_key_by_prefix.assert_called_with(mock_db, "test-api")
        mock_user_queries.get_user_by_id.assert_called_with(mock_db, mock_api_key.user_id)

        # Test invalid API key
        mock_api_key.verify_key.return_value = False
        with pytest.raises(InvalidApiKeyError):
            await get_user_from_api_key(mock_db, "invalid-key")

        # Test expired API key
        mock_api_key.verify_key.return_value = True
        mock_api_key.expires_at = now_utc() - timedelta(days=1)
        mock_api_key.status = ApiKeyStatus.EXPIRED
        with pytest.raises(InvalidApiKeyError):
            await get_user_from_api_key(mock_db, "expired-key")

        # Test non-existent API key
        mock_api_key_queries.get_api_key_by_prefix.return_value = None
        with pytest.raises(InvalidApiKeyError):
            await get_user_from_api_key(mock_db, "nonexistent-key")


@pytest.mark.asyncio
async def test_get_session_user(mock_db, mock_user, mock_request):
    """Test getting user from session."""
    with patch('app.core.authentication.user_queries') as mock_user_queries:
        # Make query function async
        mock_user_queries.get_user_by_email = AsyncMock(return_value=mock_user)

        # Test with valid session
        mock_request.session = {"user": {"email": "test@example.com"}}
        user = await get_session_user(mock_request, mock_db)
        assert user == mock_user
        mock_user_queries.get_user_by_email.assert_called_with(mock_db, "test@example.com")

        # Test with no session
        mock_request.session = {}
        user = await get_session_user(mock_request, mock_db)
        assert user is None

        # Test with invalid user status
        mock_user.status = UserStatus.INACTIVE
        mock_request.session = {"user": {"email": "test@example.com"}}
        user = await get_session_user(mock_request, mock_db)
        assert user is None

        # Test with non-existent user
        mock_user_queries.get_user_by_email.return_value = None
        user = await get_session_user(mock_request, mock_db)
        assert user is None


@pytest.mark.asyncio
async def test_get_current_active_user(mock_db, mock_user):
    """Test getting current active user."""
    mock_create_stripe = AsyncMock()

    with patch('app.core.authentication.create_stripe_customer', mock_create_stripe):
        # Test with valid session user with existing stripe customer
        user = await get_current_active_user(
            user=mock_user,
            api_key=None,
            db=mock_db
        )
        assert user == mock_user
        mock_create_stripe.assert_not_called()

        # Test Stripe customer creation
        mock_user.stripe_customer_id = None
        user = await get_current_active_user(
            user=mock_user,
            api_key=None,
            db=mock_db
        )
        assert user == mock_user
        mock_create_stripe.assert_called_once_with(mock_db, mock_user)

        # Test with no authentication
        with pytest.raises(UnauthorizedError):
            await get_current_active_user(
                user=None,
                api_key=None,
                db=mock_db
            )


@pytest.mark.asyncio
async def test_admin_required(mock_user):
    """Test admin access requirement."""
    # Test with non-admin user
    with pytest.raises(ForbiddenError):
        admin_required(mock_user)

    # Test with admin user
    mock_user.is_admin = True
    user = admin_required(mock_user)
    assert user == mock_user
