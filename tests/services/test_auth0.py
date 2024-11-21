from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote
from uuid import uuid4

import pytest
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from app.core.constants import BillingTransactionType
from app.services.auth0 import Auth0Service


@pytest.fixture
def mock_oauth():
    """Create a mock OAuth instance."""
    oauth = MagicMock(spec=OAuth)
    oauth.auth0 = MagicMock()
    return oauth


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock(spec=Request)
    request.url_for.return_value = "http://callback-url"
    request.base_url = "http://base-url"
    return request


@pytest.fixture
def auth0_service(mock_oauth):
    """Create an Auth0Service instance with mocked OAuth."""
    service = Auth0Service(mock_oauth)
    service.client_id = "test-client-id"
    service.domain = "test.auth0.com"
    service.ui_url = "http://ui-url"
    service.use_api_ui = False
    service.new_user_credits = 5.0
    return service


@pytest.mark.asyncio
async def test_get_login_url_success(auth0_service, mock_request):
    """Test successful generation of login URL."""
    # Mock authorize_redirect
    mock_response = MagicMock()
    mock_response.headers = {"location": "http://auth0-login-url"}
    auth0_service.oauth.auth0.authorize_redirect = AsyncMock(return_value=mock_response)

    # Get login URL
    login_url = await auth0_service.get_login_url(mock_request)

    # Verify
    assert login_url == "http://auth0-login-url"
    auth0_service.oauth.auth0.authorize_redirect.assert_awaited_once_with(
        mock_request, "http://callback-url"
    )


@pytest.mark.asyncio
async def test_get_login_url_error(auth0_service, mock_request):
    """Test error handling in login URL generation."""
    # Mock authorize_redirect to raise exception
    auth0_service.oauth.auth0.authorize_redirect = AsyncMock(side_effect=Exception("Auth error"))

    # Attempt to get login URL
    with pytest.raises(Exception) as exc_info:
        await auth0_service.get_login_url(mock_request)
    assert str(exc_info.value) == "Auth error"


def test_get_logout_url_with_ui(auth0_service, mock_request):
    """Test logout URL generation with UI redirect."""
    auth0_service.use_api_ui = False
    logout_url = auth0_service.get_logout_url(mock_request)

    expected_url = (
        f"https://{auth0_service.domain}/v2/logout?"
        f"returnTo={quote(auth0_service.ui_url, safe='')}&"
        f"client_id={auth0_service.client_id}"
    )
    assert logout_url == expected_url


def test_get_logout_url_without_ui(auth0_service, mock_request):
    """Test logout URL generation without UI redirect."""
    auth0_service.use_api_ui = True
    logout_url = auth0_service.get_logout_url(mock_request)

    expected_url = (
        f"https://{auth0_service.domain}/v2/logout?"
        f"returnTo={quote(mock_request.base_url, safe='')}&"
        f"client_id={auth0_service.client_id}"
    )
    assert logout_url == expected_url


@pytest.mark.asyncio
async def test_handle_callback_success(auth0_service, mock_request, mock_db):
    """Test successful callback handling."""
    # Mock user info from Auth0
    user_info = {
        "email": "test@example.com",
        "name": "Test User",
        "sub": "auth0|123",
        "email_verified": True
    }
    token = {"userinfo": user_info}
    auth0_service.oauth.auth0.authorize_access_token = AsyncMock(return_value=token)

    # Create mock user with actual attribute values
    mock_user = MagicMock(spec=['id', 'email', 'name'])
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"  # Set actual name value
    mock_user.email_verified = True
    mock_get_user = AsyncMock(return_value=mock_user)

    with patch('app.services.auth0.user_queries.get_user_by_email', mock_get_user), \
            patch('app.core.stripe_client.create_stripe_customer', AsyncMock()):
        session_data, user = await auth0_service.handle_callback(mock_request, mock_db)

        # Verify session data
        assert session_data['email'] == user_info['email']
        assert session_data['name'] == user_info['name']
        assert session_data['id'] == str(mock_user.id)

        # Verify user object
        assert user == mock_user


@pytest.mark.asyncio
async def test_handle_callback_new_user(auth0_service, mock_request, mock_db):
    """Test callback handling with new user creation."""
    # Mock user info from Auth0
    user_info = {
        "email": "new@example.com",
        "name": "New User",
        "sub": "auth0|456",
        "email_verified": True
    }
    token = {"userinfo": user_info}
    auth0_service.oauth.auth0.authorize_access_token = AsyncMock(return_value=token)

    # Mock database queries
    mock_get_user = AsyncMock(return_value=None)
    mock_user = MagicMock(id=uuid4(), email="new@example.com")

    with patch('app.services.auth0.user_queries.get_user_by_email', mock_get_user), \
            patch('app.services.auth0.add_credits_to_user', AsyncMock()), \
            patch('app.services.auth0.User') as mock_user_class, \
            patch('app.core.stripe_client.create_stripe_customer', AsyncMock()):
        mock_user_class.return_value = mock_user

        session_data, user = await auth0_service.handle_callback(mock_request, mock_db)

        # Verify user creation
        mock_db.add.assert_called_once_with(mock_user)
        mock_db.commit.assert_called()

        # Verify credits added
        from app.services.auth0 import add_credits_to_user
        add_credits_to_user.assert_awaited_once_with(
            mock_db,
            mock_user.id,
            auth0_service.new_user_credits,
            "NEW_USER_CREDIT",
            BillingTransactionType.NEW_USER_CREDIT
        )


@pytest.mark.asyncio
async def test_handle_callback_missing_user_info(auth0_service, mock_request, mock_db):
    """Test callback handling with missing user info."""
    # Mock token without user info
    token = {"userinfo": None}
    auth0_service.oauth.auth0.authorize_access_token = AsyncMock(return_value=token)

    with pytest.raises(ValueError) as exc_info:
        await auth0_service.handle_callback(mock_request, mock_db)
    assert "No user info found in Auth0 token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_callback_error(auth0_service, mock_request, mock_db):
    """Test error handling during callback."""
    # Mock authorize_access_token to raise exception
    auth0_service.oauth.auth0.authorize_access_token = AsyncMock(
        side_effect=Exception("Token error")
    )

    with pytest.raises(Exception) as exc_info:
        await auth0_service.handle_callback(mock_request, mock_db)
    assert str(exc_info.value) == "Token error"
