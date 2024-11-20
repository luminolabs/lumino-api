from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.constants import BaseModelStatus
from app.core.exceptions import BaseModelNotFoundError
from app.models.base_model import BaseModel
from app.services.model import get_base_models, get_base_model


@pytest.fixture
def mock_base_model():
    """Create a mock base model object."""
    model = MagicMock(spec=BaseModel)
    model.id = UUID('12345678-1234-5678-1234-567812345678')
    model.name = "llm_llama3_1_8b"
    model.description = "Test model"
    model.hf_url = "https://huggingface.co/test-model"
    model.status = BaseModelStatus.ACTIVE
    model.meta = {"key": "value"}
    return model


@pytest.mark.asyncio
async def test_get_base_models_success(mock_db, mock_base_model):
    """Test successful retrieval of base models list."""
    with patch('app.services.model.model_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_base_models = AsyncMock(return_value=1)
        mock_queries.list_base_models = AsyncMock(return_value=[mock_base_model])

        # Call function
        result, pagination = await get_base_models(mock_db)

        # Verify results
        assert len(result) == 1
        model_response = result[0]
        assert model_response.name == mock_base_model.name
        assert model_response.description == mock_base_model.description
        assert model_response.hf_url == mock_base_model.hf_url
        assert model_response.status == mock_base_model.status
        assert model_response.meta == mock_base_model.meta

        # Verify pagination
        assert pagination.total_pages == 1
        assert pagination.current_page == 1
        assert pagination.items_per_page == 20

        # Verify query calls
        mock_queries.count_base_models.assert_awaited_once_with(mock_db)
        mock_queries.list_base_models.assert_awaited_once_with(
            mock_db, 0, 20
        )


@pytest.mark.asyncio
async def test_get_base_models_empty(mock_db):
    """Test retrieving empty base models list."""
    with patch('app.services.model.model_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_base_models = AsyncMock(return_value=0)
        mock_queries.list_base_models = AsyncMock(return_value=[])

        # Call function
        result, pagination = await get_base_models(mock_db)

        # Verify results
        assert len(result) == 0
        assert pagination.total_pages == 0
        assert pagination.current_page == 1
        assert pagination.items_per_page == 20


@pytest.mark.asyncio
async def test_get_base_models_pagination(mock_db, mock_base_model):
    """Test base models list pagination."""
    with patch('app.services.model.model_queries') as mock_queries:
        # Configure mocks for second page
        mock_queries.count_base_models = AsyncMock(return_value=25)
        mock_queries.list_base_models = AsyncMock(return_value=[mock_base_model])

        # Call function with page 2
        result, pagination = await get_base_models(mock_db, page=2, items_per_page=10)

        # Verify pagination
        assert pagination.total_pages == 3
        assert pagination.current_page == 2
        assert pagination.items_per_page == 10

        # Verify correct offset in query
        mock_queries.list_base_models.assert_awaited_once_with(
            mock_db, 10, 10
        )


@pytest.mark.asyncio
async def test_get_base_model_success(mock_db, mock_base_model):
    """Test successful retrieval of specific base model."""
    with patch('app.services.model.model_queries') as mock_queries:
        mock_queries.get_base_model_by_name = AsyncMock(return_value=mock_base_model)

        result = await get_base_model(mock_db, "llm_llama3_1_8b")

        assert result.name == mock_base_model.name
        assert result.description == mock_base_model.description
        assert result.hf_url == mock_base_model.hf_url
        assert result.status == mock_base_model.status
        assert result.meta == mock_base_model.meta

        mock_queries.get_base_model_by_name.assert_awaited_once_with(
            mock_db, "llm_llama3_1_8b"
        )


@pytest.mark.asyncio
async def test_get_base_model_not_found(mock_db):
    """Test retrieving non-existent base model."""
    with patch('app.services.model.model_queries') as mock_queries:
        mock_queries.get_base_model_by_name = AsyncMock(return_value=None)

        with pytest.raises(BaseModelNotFoundError) as exc_info:
            await get_base_model(mock_db, "nonexistent-model")

        assert "Base model not found: nonexistent-model" in str(exc_info.value)