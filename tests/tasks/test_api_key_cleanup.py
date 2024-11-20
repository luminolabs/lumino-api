from unittest.mock import AsyncMock, patch

import pytest

from app.tasks.api_key_cleanup import cleanup_expired_api_keys


@pytest.mark.asyncio
async def test_cleanup_expired_api_keys_success(mock_db):
    """Test successful cleanup of expired API keys."""
    with patch('app.tasks.api_key_cleanup.api_key_queries') as mock_queries:
        # Configure mock to indicate 3 keys were updated
        mock_queries.mark_expired_keys = AsyncMock(return_value=3)

        # Execute cleanup
        await cleanup_expired_api_keys(mock_db)

        # Verify queries and database operations
        mock_queries.mark_expired_keys.assert_awaited_once_with(mock_db)
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_expired_api_keys_no_expired(mock_db):
    """Test cleanup when no expired keys are found."""
    with patch('app.tasks.api_key_cleanup.api_key_queries') as mock_queries:
        # Configure mock to indicate no keys were updated
        mock_queries.mark_expired_keys = AsyncMock(return_value=0)

        # Execute cleanup
        await cleanup_expired_api_keys(mock_db)

        # Verify queries and database operations
        mock_queries.mark_expired_keys.assert_awaited_once_with(mock_db)
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_expired_api_keys_error(mock_db):
    """Test cleanup error handling."""
    with patch('app.tasks.api_key_cleanup.api_key_queries') as mock_queries:
        # Configure mock to raise an exception
        mock_queries.mark_expired_keys = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute cleanup
        await cleanup_expired_api_keys(mock_db)

        # Verify error handling
        mock_queries.mark_expired_keys.assert_awaited_once_with(mock_db)
        mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_expired_api_keys_commit_error(mock_db):
    """Test handling of database commit error."""
    with patch('app.tasks.api_key_cleanup.api_key_queries') as mock_queries:
        # Configure mocks
        mock_queries.mark_expired_keys = AsyncMock(return_value=2)
        mock_db.commit.side_effect = Exception("Commit error")

        # Execute cleanup
        await cleanup_expired_api_keys(mock_db)

        # Verify error handling
        mock_queries.mark_expired_keys.assert_awaited_once_with(mock_db)
        mock_db.rollback.assert_awaited_once()