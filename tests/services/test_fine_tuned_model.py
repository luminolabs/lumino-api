from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.constants import FineTunedModelStatus
from app.core.exceptions import FineTunedModelNotFoundError
from app.models.fine_tuned_model import FineTunedModel
from app.services.fine_tuned_model import (
    get_fine_tuned_models,
    get_fine_tuned_model,
    create_fine_tuned_model
)


@pytest.fixture
def mock_user_id():
    """Create a mock user ID."""
    return UUID('12345678-1234-5678-1234-567812345678')

@pytest.fixture
def mock_job_id():
    """Create a mock job ID."""
    return UUID('98765432-9876-5432-9876-987654321098')

@pytest.fixture
def mock_fine_tuned_model():
    """Create a mock fine-tuned model object."""
    model = MagicMock(spec=FineTunedModel)
    model.id = uuid4()
    model.created_at = datetime.utcnow()
    model.updated_at = datetime.utcnow()
    model.user_id = UUID('12345678-1234-5678-1234-567812345678')
    model.fine_tuning_job_id = UUID('98765432-9876-5432-9876-987654321098')
    model.name = "test-model"
    model.status = FineTunedModelStatus.ACTIVE
    model.artifacts = {"weights": "model.pt"}
    return model

@pytest.mark.asyncio
async def test_get_fine_tuned_models(mock_db, mock_user_id, mock_fine_tuned_model):
    """Test retrieving fine-tuned models list."""
    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_models = AsyncMock(return_value=1)
        mock_queries.list_models = AsyncMock(return_value=[(mock_fine_tuned_model, "test-job")])

        # Call function
        result, pagination = await get_fine_tuned_models(mock_db, mock_user_id)

        # Verify results
        assert len(result) == 1
        assert result[0].name == mock_fine_tuned_model.name
        assert result[0].fine_tuning_job_name == "test-job"
        assert pagination.total_pages == 1
        assert pagination.current_page == 1

        # Verify query calls
        mock_queries.count_models.assert_awaited_once_with(mock_db, mock_user_id)
        mock_queries.list_models.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_fine_tuned_model_success(mock_db, mock_user_id, mock_fine_tuned_model):
    """Test retrieving a specific fine-tuned model."""
    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_queries:
        mock_queries.get_model_by_name = AsyncMock(
            return_value=(mock_fine_tuned_model, "test-job")
        )

        result = await get_fine_tuned_model(mock_db, mock_user_id, "test-model")

        assert result.name == mock_fine_tuned_model.name
        assert result.fine_tuning_job_name == "test-job"
        mock_queries.get_model_by_name.assert_awaited_once_with(
            mock_db, mock_user_id, "test-model"
        )

@pytest.mark.asyncio
async def test_get_fine_tuned_model_not_found(mock_db, mock_user_id):
    """Test retrieving a non-existent fine-tuned model."""
    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_queries:
        mock_queries.get_model_by_name = AsyncMock(return_value=None)

        with pytest.raises(FineTunedModelNotFoundError):
            await get_fine_tuned_model(mock_db, mock_user_id, "nonexistent-model")

@pytest.mark.asyncio
async def test_create_fine_tuned_model_success(mock_db, mock_user_id, mock_job_id):
    """Test successful fine-tuned model creation."""
    # Mock artifacts
    artifacts = {"weights": "model.pt"}

    # Mock job and queries
    mock_job = MagicMock()
    mock_job.id = mock_job_id
    mock_job.name = "test-job"
    mock_job.user_id = mock_user_id

    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_ft_queries, \
            patch('app.services.fine_tuned_model.app.queries.fine_tuning') as mock_ft_job_queries:

        # Configure mocks
        mock_ft_queries.get_existing_model = AsyncMock(return_value=None)
        mock_ft_queries.create_model = AsyncMock()
        mock_ft_job_queries.get_job_by_id = AsyncMock(return_value=mock_job)

        # Call function
        result = await create_fine_tuned_model(mock_db, mock_job_id, mock_user_id, artifacts)

        # Verify results
        assert result is True
        mock_ft_queries.create_model.assert_awaited_once_with(
            mock_db,
            mock_job_id,
            mock_user_id,
            "test-job_model",
            artifacts
        )
        mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_fine_tuned_model_existing(mock_db, mock_user_id, mock_job_id, mock_fine_tuned_model):
    """Test model creation when model already exists."""
    artifacts = {"weights": "model.pt"}

    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_queries:
        mock_queries.get_existing_model = AsyncMock(return_value=mock_fine_tuned_model)

        result = await create_fine_tuned_model(mock_db, mock_job_id, mock_user_id, artifacts)

        assert result is True
        mock_queries.create_model.assert_not_called()
        mock_db.commit.assert_not_awaited()

@pytest.mark.asyncio
async def test_create_fine_tuned_model_job_not_found(mock_db, mock_user_id, mock_job_id):
    """Test model creation when job not found."""
    artifacts = {"weights": "model.pt"}

    with patch('app.services.fine_tuned_model.app.queries.fine_tuning') as mock_queries:
        mock_queries.get_job_by_id = AsyncMock(return_value=None)

        result = await create_fine_tuned_model(mock_db, mock_job_id, mock_user_id, artifacts)

        assert result is False
        mock_db.commit.assert_not_awaited()

@pytest.mark.asyncio
async def test_create_fine_tuned_model_error(mock_db, mock_user_id, mock_job_id):
    """Test model creation with error."""
    artifacts = {"weights": "model.pt"}
    mock_job = MagicMock()
    mock_job.id = mock_job_id
    mock_job.name = "test-job"
    mock_job.user_id = mock_user_id

    with patch('app.services.fine_tuned_model.ft_models_queries') as mock_ft_queries, \
            patch('app.services.fine_tuned_model.app.queries.fine_tuning') as mock_ft_job_queries:

        # Configure mocks
        mock_ft_queries.get_existing_model = AsyncMock(return_value=None)
        mock_ft_queries.create_model = AsyncMock(side_effect=Exception("Database error"))
        mock_ft_job_queries.get_job_by_id = AsyncMock(return_value=mock_job)

        result = await create_fine_tuned_model(mock_db, mock_job_id, mock_user_id, artifacts)

        assert result is False
        mock_db.rollback.assert_awaited_once()