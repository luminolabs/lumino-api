from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.constants import ApiKeyStatus
from app.core.exceptions import ApiKeyAlreadyExistsError, ApiKeyNotFoundError
from app.models.api_key import ApiKey
from app.queries.common import now_utc
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate
from app.services.api_key import (
    create_api_key,
    get_api_keys,
    get_api_key,
    update_api_key,
    revoke_api_key
)


@pytest.fixture
def mock_user_id():
    """Create a mock user ID."""
    return uuid4()


@pytest.fixture
def mock_api_key():
    """Create a mock API key object."""
    api_key = MagicMock(spec=ApiKey)
    api_key.id = uuid4()
    api_key.name = "test-key"
    api_key.prefix = "test1234"
    api_key.status = ApiKeyStatus.ACTIVE
    api_key.expires_at = now_utc() + timedelta(days=1)
    return api_key


@pytest.mark.asyncio
async def test_create_api_key_success(mock_db, mock_user_id):
    """Test successful API key creation."""
    # Set up test data
    key_create = ApiKeyCreate(
        name="test-key",
        expires_at=now_utc() + timedelta(days=1)
    )

    # Mock dependencies
    with patch('app.services.api_key.api_key_queries') as mock_queries, \
            patch('app.services.api_key.generate_api_key') as mock_generate:
        # Configure mocks
        mock_queries.get_api_key_by_name = AsyncMock(return_value=None)
        mock_generate.return_value = ("test-api-key", "hashed-key")

        # Call function
        result = await create_api_key(mock_db, mock_user_id, key_create)

        # Verify result
        assert result.name == "test-key"
        assert result.secret == "test-api-key"
        assert result.status == ApiKeyStatus.ACTIVE

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_api_key_duplicate(mock_db, mock_user_id, mock_api_key):
    """Test API key creation with duplicate name."""
    key_create = ApiKeyCreate(
        name="existing-key",
        expires_at=now_utc() + timedelta(days=1)
    )

    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=mock_api_key)

        with pytest.raises(ApiKeyAlreadyExistsError):
            await create_api_key(mock_db, mock_user_id, key_create)


@pytest.mark.asyncio
async def test_get_api_keys(mock_db, mock_user_id, mock_api_key):
    """Test retrieving API keys list."""
    with patch('app.services.api_key.api_key_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_api_keys = AsyncMock(return_value=1)
        mock_queries.list_api_keys = AsyncMock(return_value=[mock_api_key])

        # Call function
        result, pagination = await get_api_keys(mock_db, mock_user_id)

        # Verify results
        assert len(result) == 1
        assert result[0].name == mock_api_key.name
        assert pagination.total_pages == 1
        assert pagination.current_page == 1

        # Verify query calls
        mock_queries.count_api_keys.assert_awaited_once_with(mock_db, mock_user_id)
        mock_queries.list_api_keys.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_api_key_success(mock_db, mock_user_id, mock_api_key):
    """Test retrieving a specific API key."""
    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=mock_api_key)

        result = await get_api_key(mock_db, mock_user_id, "test-key")

        assert result.name == mock_api_key.name
        mock_queries.get_api_key_by_name.assert_awaited_once_with(
            mock_db, mock_user_id, "test-key"
        )


@pytest.mark.asyncio
async def test_get_api_key_not_found(mock_db, mock_user_id):
    """Test retrieving a non-existent API key."""
    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=None)

        with pytest.raises(ApiKeyNotFoundError):
            await get_api_key(mock_db, mock_user_id, "nonexistent-key")


@pytest.mark.asyncio
async def test_update_api_key_success(mock_db, mock_user_id, mock_api_key):
    """Test successful API key update."""
    key_update = ApiKeyUpdate(
        name="updated-key",
        expires_at=now_utc() + timedelta(days=2)
    )

    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(side_effect=[mock_api_key, None])

        result = await update_api_key(mock_db, mock_user_id, "test-key", key_update)

        assert result.name == mock_api_key.name
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_api_key_not_found(mock_db, mock_user_id):
    """Test updating a non-existent API key."""
    key_update = ApiKeyUpdate(name="updated-key")

    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=None)

        with pytest.raises(ApiKeyNotFoundError):
            await update_api_key(mock_db, mock_user_id, "nonexistent-key", key_update)


@pytest.mark.asyncio
async def test_revoke_api_key_success(mock_db, mock_user_id, mock_api_key):
    """Test successful API key revocation."""
    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=mock_api_key)

        result = await revoke_api_key(mock_db, mock_user_id, "test-key")

        assert result.status == ApiKeyStatus.REVOKED
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_api_key_not_found(mock_db, mock_user_id):
    """Test revoking a non-existent API key."""
    with patch('app.services.api_key.api_key_queries') as mock_queries:
        mock_queries.get_api_key_by_name = AsyncMock(return_value=None)

        with pytest.raises(ApiKeyNotFoundError):
            await revoke_api_key(mock_db, mock_user_id, "nonexistent-key")
