from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile

from app.core.constants import DatasetStatus
from app.core.exceptions import DatasetAlreadyExistsError, DatasetNotFoundError
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetUpdate
from app.services.dataset import (
    create_dataset,
    get_datasets,
    get_dataset,
    update_dataset,
    delete_dataset
)


@pytest.fixture
def mock_user_id():
    """Create a mock user ID."""
    return UUID('12345678-1234-5678-1234-567812345678')


@pytest.fixture
def mock_dataset():
    """Create a mock dataset object."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = uuid4()
    dataset.created_at = datetime.utcnow()
    dataset.updated_at = datetime.utcnow()
    dataset.user_id = UUID('12345678-1234-5678-1234-567812345678')
    dataset.status = DatasetStatus.UPLOADED
    dataset.name = "test-dataset"
    dataset.description = "Test dataset description"
    dataset.file_name = "test_file.jsonl"
    dataset.file_size = 1024
    dataset.errors = None
    return dataset


@pytest.fixture
def mock_upload_file():
    """Create a mock upload file."""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_file.jsonl"
    file.content_type = "application/json"
    file.size = 1024
    return file


@pytest.mark.asyncio
async def test_create_dataset_success(mock_db, mock_user_id, mock_upload_file):
    """Test successful dataset creation."""
    dataset_create = DatasetCreate(
        name="test-dataset",
        description="Test dataset description",
        file=mock_upload_file
    )

    with patch('app.services.dataset.dataset_queries') as mock_queries, \
            patch('app.services.dataset.upload_file') as mock_upload:
        # Configure mocks
        mock_queries.get_dataset_by_name = AsyncMock(return_value=None)
        mock_upload.return_value = "uploaded_file.jsonl"

        # Call function
        result = await create_dataset(mock_db, mock_user_id, dataset_create)

        # Verify result
        assert result.name == "test-dataset"
        assert result.status == DatasetStatus.UPLOADED
        assert result.file_name == "uploaded_file.jsonl"

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        # Verify file upload
        mock_upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_dataset_exists(mock_db, mock_user_id, mock_upload_file, mock_dataset):
    """Test dataset creation with duplicate name."""
    dataset_create = DatasetCreate(
        name="existing-dataset",
        description="Test dataset description",
        file=mock_upload_file
    )

    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)

        with pytest.raises(DatasetAlreadyExistsError):
            await create_dataset(mock_db, mock_user_id, dataset_create)


@pytest.mark.asyncio
async def test_create_dataset_upload_error(mock_db, mock_user_id, mock_upload_file):
    """Test dataset creation with upload error."""
    dataset_create = DatasetCreate(
        name="test-dataset",
        description="Test dataset description",
        file=mock_upload_file
    )

    with patch('app.services.dataset.dataset_queries') as mock_queries, \
            patch('app.services.dataset.upload_file') as mock_upload:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=None)
        mock_upload.side_effect = Exception("Upload failed")

        with pytest.raises(Exception):
            await create_dataset(mock_db, mock_user_id, dataset_create)
            mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_datasets(mock_db, mock_user_id, mock_dataset):
    """Test retrieving datasets list."""
    with patch('app.services.dataset.dataset_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_datasets = AsyncMock(return_value=1)
        mock_queries.list_datasets = AsyncMock(return_value=[mock_dataset])

        # Get datasets
        result, pagination = await get_datasets(mock_db, mock_user_id)

        # Verify results
        assert len(result) == 1
        assert result[0].name == mock_dataset.name
        assert pagination.total_pages == 1
        assert pagination.current_page == 1

        # Verify query calls
        mock_queries.count_datasets.assert_awaited_once_with(mock_db, mock_user_id)
        mock_queries.list_datasets.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_dataset_success(mock_db, mock_user_id, mock_dataset):
    """Test retrieving a specific dataset."""
    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)

        result = await get_dataset(mock_db, mock_user_id, "test-dataset")

        assert result.name == mock_dataset.name
        mock_queries.get_dataset_by_name.assert_awaited_once_with(
            mock_db, mock_user_id, "test-dataset"
        )


@pytest.mark.asyncio
async def test_get_dataset_not_found(mock_db, mock_user_id):
    """Test retrieving a non-existent dataset."""
    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=None)

        with pytest.raises(DatasetNotFoundError):
            await get_dataset(mock_db, mock_user_id, "nonexistent-dataset")


@pytest.mark.asyncio
async def test_update_dataset_success(mock_db, mock_user_id, mock_dataset):
    """Test successful dataset update."""
    dataset_update = DatasetUpdate(
        name="updated-dataset",
        description="Updated description"
    )

    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)

        result = await update_dataset(mock_db, mock_user_id, "test-dataset", dataset_update)

        assert result.name == mock_dataset.name
        assert result.description == mock_dataset.description
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_dataset_not_found(mock_db, mock_user_id):
    """Test updating a non-existent dataset."""
    dataset_update = DatasetUpdate(name="updated-dataset")

    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=None)

        with pytest.raises(DatasetNotFoundError):
            await update_dataset(mock_db, mock_user_id, "nonexistent-dataset", dataset_update)


@pytest.mark.asyncio
async def test_delete_dataset_success(mock_db, mock_user_id, mock_dataset):
    """Test successful dataset deletion."""
    with patch('app.services.dataset.dataset_queries') as mock_queries, \
            patch('app.services.dataset.delete_file') as mock_delete:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)
        mock_delete.return_value = None

        await delete_dataset(mock_db, mock_user_id, "test-dataset")

        # Verify dataset marked as deleted
        assert mock_dataset.status == DatasetStatus.DELETED
        mock_db.commit.assert_awaited_once()

        # Verify file deletion
        mock_delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_dataset_not_found(mock_db, mock_user_id):
    """Test deleting a non-existent dataset."""
    with patch('app.services.dataset.dataset_queries') as mock_queries:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=None)

        with pytest.raises(DatasetNotFoundError):
            await delete_dataset(mock_db, mock_user_id, "nonexistent-dataset")


@pytest.mark.asyncio
async def test_delete_dataset_error(mock_db, mock_user_id, mock_dataset):
    """Test dataset deletion with error."""
    with patch('app.services.dataset.dataset_queries') as mock_queries, \
            patch('app.services.dataset.delete_file') as mock_delete:
        mock_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)
        mock_delete.side_effect = Exception("Delete failed")

        with pytest.raises(Exception):
            await delete_dataset(mock_db, mock_user_id, "test-dataset")
            mock_db.rollback.assert_awaited_once()
