from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.api_core.exceptions import NotFound

from app.queries.common import now_utc
from app.tasks.model_cleanup import cleanup_deleted_model_weights, _cleanup_model_weights


@pytest.fixture
def mock_storage_client():
    """Create a mock Google Cloud Storage client."""
    client = MagicMock()
    bucket = MagicMock()
    client.bucket.return_value = bucket
    return client


@pytest.fixture
def mock_deleted_model():
    """Create a mock deleted fine-tuned model."""
    model = MagicMock()
    model.id = "test-model-id"
    model.artifacts = {
        "base_url": "gs://test-bucket/datasets/user123/job456",
        "weight_files": ["model.pt", "optimizer.pt"]
    }
    return model


@pytest.mark.asyncio
async def test_cleanup_deleted_models_success(mock_db, mock_storage_client, mock_deleted_model):
    """Test successful cleanup of deleted model weights."""
    now_utc_ = now_utc()
    three_days_ago = now_utc_ - timedelta(days=3)

    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.storage.Client', return_value=mock_storage_client), \
            patch('app.tasks.model_cleanup.now_utc', return_value=now_utc_):

        # Configure mock to return one deleted model
        mock_queries.get_deleted_models = AsyncMock(return_value=[mock_deleted_model])

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify queries and operations
        mock_queries.get_deleted_models.assert_awaited_once_with(
            mock_db,
            three_days_ago
        )

        # Verify storage operations
        bucket = mock_storage_client.bucket.return_value
        assert bucket.blob.call_count == 2  # Two weight files
        bucket.blob.assert_any_call("user123/job456/model.pt")
        bucket.blob.assert_any_call("user123/job456/optimizer.pt")

        # Verify each blob was deleted
        for call in bucket.blob.return_value.mock_calls:
            if call[0] == 'delete':
                assert len(call[1]) == 0  # delete() was called with no arguments

        # Verify artifacts were updated
        assert mock_deleted_model.artifacts["weight_files"] == []
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_deleted_models_no_models(mock_db):
    """Test cleanup when no deleted models are found."""
    with patch('app.tasks.model_cleanup.model_queries') as mock_queries:
        # Configure mock to return no models
        mock_queries.get_deleted_models = AsyncMock(return_value=[])

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify queries
        mock_queries.get_deleted_models.assert_awaited_once()
        # Verify no commit was made
        mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_deleted_models_no_artifacts(mock_db, mock_storage_client):
    """Test cleanup with model having no artifacts."""
    model = MagicMock()
    model.artifacts = None

    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.storage.Client', return_value=mock_storage_client):
        mock_queries.get_deleted_models = AsyncMock(return_value=[model])

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify no storage operations were performed
        mock_storage_client.bucket.assert_not_called()
        # Verify commit was still made
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_model_weights_file_not_found(mock_storage_client, mock_deleted_model):
    """Test handling of NotFound error during weight file deletion."""
    # Configure storage client to raise NotFound for deletion
    blob_mock = MagicMock()
    blob_mock.delete.side_effect = NotFound("Blob not found")
    bucket = mock_storage_client.bucket.return_value
    bucket.blob.return_value = blob_mock

    # Execute cleanup
    result = await _cleanup_model_weights(mock_deleted_model, mock_storage_client)

    # Verify an error occurred
    assert result is None


@pytest.mark.asyncio
async def test_cleanup_deleted_models_error(mock_db, mock_storage_client, mock_deleted_model):
    """Test error handling during cleanup."""
    with patch('app.tasks.model_cleanup.model_queries') as mock_queries, \
            patch('app.tasks.model_cleanup.storage.Client', return_value=mock_storage_client):
        # Configure mock to raise an exception
        mock_queries.get_deleted_models = AsyncMock(side_effect=Exception("Database error"))

        # Execute cleanup
        await cleanup_deleted_model_weights(mock_db)

        # Verify rollback was called
        mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_model_weights_invalid_url(mock_storage_client, mock_deleted_model):
    """Test cleanup with invalid GCS URL format."""
    # Set invalid GCS URL
    mock_deleted_model.artifacts["base_url"] = "invalid-url"

    # Execute cleanup
    result = await _cleanup_model_weights(mock_deleted_model, mock_storage_client)

    # Verify no storage operations were attempted
    mock_storage_client.bucket.assert_not_called()
    # Verify an error occurred
    assert result is None


@pytest.mark.asyncio
async def test_cleanup_model_weights_empty_weight_files(mock_storage_client, mock_deleted_model):
    """Test cleanup with empty weight files list."""
    # Set empty weight files list
    mock_deleted_model.artifacts["weight_files"] = []

    # Execute cleanup
    result = await _cleanup_model_weights(mock_deleted_model, mock_storage_client)

    # Verify no storage operations were attempted
    mock_storage_client.bucket.blob.assert_not_called()
    # Verify an error occurred
    assert result is None
