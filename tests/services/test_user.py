from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.constants import UserStatus, BillingTransactionType
from app.core.exceptions import UserNotFoundError
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.user import (
    update_user,
    deactivate_user,
    create_user
)


@pytest.fixture
def mock_user():
    """Create a mock user with necessary attributes."""
    user = MagicMock(spec=User)
    user.id = UUID('12345678-1234-5678-1234-567812345678')
    user.email = "test@example.com"
    user.name = "Test User"
    user.status = UserStatus.ACTIVE
    user.auth0_user_id = "auth0|123"
    user.email_verified = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


@pytest.mark.asyncio
async def test_update_user_success(mock_db, mock_user):
    """Test successful user update."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    user_update = UserUpdate(name="Updated Name")

    with patch('app.services.user.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=mock_user)

        result = await update_user(mock_db, user_id, user_update)

        # Verify user was updated
        assert result.name == mock_user.name
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        # Verify query call
        mock_queries.get_user_by_id.assert_awaited_once_with(mock_db, user_id)


@pytest.mark.asyncio
async def test_update_user_not_found(mock_db):
    """Test updating non-existent user."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    user_update = UserUpdate(name="Updated Name")

    with patch('app.services.user.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError) as exc_info:
            await update_user(mock_db, user_id, user_update)

        assert f"User with ID {user_id} not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_deactivate_user_success(mock_db, mock_user):
    """Test successful user deactivation."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')

    with patch('app.services.user.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=mock_user)

        await deactivate_user(mock_db, user_id)

        # Verify user was deactivated
        assert mock_user.status == UserStatus.INACTIVE
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_user_not_found(mock_db):
    """Test deactivating non-existent user."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')

    with patch('app.services.user.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError) as exc_info:
            await deactivate_user(mock_db, user_id)

        assert f"User with ID {user_id} not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_success(mock_db):
    """Test successful user creation."""
    name = "New User"
    email = "new@example.com"
    auth0_user_id = "auth0|123"
    email_verified = True

    with patch('app.services.user.add_credits_to_user') as mock_add_credits, \
            patch('app.services.user.create_stripe_customer') as mock_create_stripe:
        mock_add_credits.return_value = None
        mock_create_stripe.return_value = None

        result = await create_user(mock_db, name, email, auth0_user_id, email_verified)

        # Verify user was created
        assert isinstance(result, User)
        assert result.name == name
        assert result.email == email
        assert result.auth0_user_id == auth0_user_id
        assert result.email_verified == email_verified

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        # Verify credits were added and Stripe customer was created
        mock_add_credits.assert_awaited_once_with(
            mock_db,
            result.id,
            5.0,  # default new user credits
            "NEW_USER_CREDIT",
            BillingTransactionType.NEW_USER_CREDIT
        )
        mock_create_stripe.assert_awaited_once_with(mock_db, result)


@pytest.mark.asyncio
async def test_create_user_no_credits(mock_db):
    """Test user creation with new_user_credits set to 0."""
    name = "New User"
    email = "new@example.com"
    auth0_user_id = "auth0|123"
    email_verified = True

    with patch('app.services.user.config.new_user_credits', 0), \
            patch('app.services.user.add_credits_to_user') as mock_add_credits, \
            patch('app.services.user.create_stripe_customer') as mock_create_stripe:
        mock_create_stripe.return_value = None

        result = await create_user(mock_db, name, email, auth0_user_id, email_verified)

        # Verify user was created
        assert isinstance(result, User)

        # Verify no credits were added
        mock_add_credits.assert_not_awaited()

        # Verify Stripe customer was still created
        mock_create_stripe.assert_awaited_once_with(mock_db, result)


@pytest.mark.asyncio
async def test_create_user_error(mock_db):
    """Test user creation with database error."""
    name = "New User"
    email = "new@example.com"
    auth0_user_id = "auth0|123"
    email_verified = True

    # Simulate database error
    mock_db.commit.side_effect = Exception("Database error")

    with patch('app.services.user.add_credits_to_user'), \
            patch('app.services.user.create_stripe_customer'):
        with pytest.raises(Exception) as exc_info:
            await create_user(mock_db, name, email, auth0_user_id, email_verified)

        assert "Database error" in str(exc_info.value)
        mock_db.rollback.assert_awaited_once()
