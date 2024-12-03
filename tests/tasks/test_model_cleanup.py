from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from gcloud.aio.storage import Storage

from app.core.exceptions import StorageError
from app.models.fine_tuned_model import FineTunedModel
from app.queries.common import now_utc
from app.tasks.model_cleanup import (
    cleanup_deleted_model_weights,
    _cleanup_model_weights,
    _update_model_artifacts
)


@pytest.fixture
def mock_model():
    """Create a mock fine-tuned model."""
    model = MagicMock(spec=FineTunedModel)
    model.id = UUID('12345678-1234-5678-1234-567812345678')
    model.artifacts = {
        "base_url": "https://storage.googleapis.com/test-bucket/user123/job456",
        "weight_files": ["model.pt", "optimizer.pt"]
    }
    return model


@pytest.mark.asyncio
async def test_cleanup_deleted_model_weights_success(mock_db, mock_model):
    """Test successful cleanup of deleted model weights."""
    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.Storage') as MockStorage:
        # Configure mocks
        mock_queries.get_deleted_models = AsyncMock(return_value=[mock_model])
        mock_storage = AsyncMock(spec=Storage)
        MockStorage.return_value = mock_storage

        # Configure storage mock to succeed
        mock_storage.delete = AsyncMock()

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify storage operations
        # Two files should be deleted
        assert mock_storage.delete.await_count == 2
        mock_storage.delete.assert_any_await(
            bucket="test-bucket",
            object_name="user123/job456/model.pt"
        )
        mock_storage.delete.assert_any_await(
            bucket="test-bucket",
            object_name="user123/job456/optimizer.pt"
        )

        # Verify model artifacts were updated
        assert mock_model.artifacts["weight_files"] == []
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_deleted_model_weights_no_models(mock_db):
    """Test cleanup when no deleted models are found."""
    now = now_utc()
    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.now_utc', return_value=now):
        # Configure mock to return no models
        mock_queries.get_deleted_models = AsyncMock(return_value=[])

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify no operations were performed
        mock_queries.get_deleted_models.assert_awaited_once_with(
            mock_db,
            now - timedelta(days=3)
        )
        mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_deleted_model_weights_error(mock_db, mock_model):
    """Test error handling during cleanup."""
    with patch('app.tasks.model_cleanup.model_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_deleted_models = AsyncMock(side_effect=Exception("Database error"))

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify error handling
        mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_deleted_model_weights_invalid_url(mock_db, mock_model):
    """Test cleanup with invalid base_url format."""
    # Set invalid base URL
    mock_model.artifacts["base_url"] = "invalid-url"

    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.logger') as mock_logger:
        mock_queries.get_deleted_models = AsyncMock(return_value=[mock_model])

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify error was logged
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_model_weights_storage_error():
    """Test handling of storage errors in _cleanup_model_weights."""
    mock_model = MagicMock(spec=FineTunedModel)
    mock_model.artifacts = {
        "base_url": "https://storage.googleapis.com/test-bucket/user123/job456",
        "weight_files": ["model.pt"]
    }
    mock_storage = AsyncMock(spec=Storage)
    mock_storage.delete = AsyncMock(side_effect=StorageError("Storage error"))

    with patch('app.tasks.model_cleanup.logger') as mock_logger:
        await _cleanup_model_weights(mock_model, mock_storage)

        assert mock_logger.error.called_once()


def test_update_model_artifacts():
    """Test updating model artifacts."""
    artifacts = {
        "base_url": "https://storage.googleapis.com/test-bucket/user123/job456",
        "weight_files": ["model.pt", "optimizer.pt"],
        "other_data": {"key": "value"}
    }

    updated = _update_model_artifacts(artifacts)

    # Verify weight files are cleared but other data remains
    assert updated["weight_files"] == []
    assert updated["base_url"] == artifacts["base_url"]
    assert updated["other_data"] == artifacts["other_data"]


@pytest.mark.asyncio
async def test_cleanup_model_weights_no_artifacts(mock_db, mock_model):
    """Test cleanup when model has no artifacts."""
    mock_model.artifacts = None

    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.Storage') as MockStorage:
        mock_queries.get_deleted_models = AsyncMock(return_value=[mock_model])
        mock_storage = AsyncMock(spec=Storage)
        MockStorage.return_value = mock_storage

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify no storage operations were attempted
        mock_storage.delete.assert_not_awaited()
        # Verify transaction was still committed
        mock_db.commit.assert_awaited_once()
