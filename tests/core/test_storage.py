from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from aiohttp import ClientResponseError, ClientSession
from gcloud.aio.storage import Storage

from app.core.exceptions import ServerError, StorageError
from app.core.storage import upload_file, delete_file, handle_gcs_error


@pytest.fixture
def mock_file():
    """Create a mock uploaded file."""
    file = AsyncMock()
    file.filename = "test_file.txt"
    file.content_type = "text/plain"
    file.read = AsyncMock(return_value=b"test content")
    file.size = len(b"test content")
    return file


@pytest.fixture
def mock_storage():
    """Create a mock Storage instance."""
    return AsyncMock(spec=Storage)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=ClientSession)
    return session


@pytest.mark.asyncio
async def test_upload_file_success(mock_file):
    """Test successful file upload."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"

    # Mock the storage client
    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.upload = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session

        # Call the function
        result = await upload_file('lum-pipeline-zen-jobs-us', path, mock_file, user_id)

        # Verify the upload was called correctly
        mock_storage.upload.assert_called_once()
        call_args = mock_storage.upload.call_args

        assert call_args[1]['bucket'] == "lum-pipeline-zen-jobs-us"
        assert "test_path" in call_args[1]['object_name']
        assert call_args[1]['content_type'] == "text/plain"
        assert isinstance(result, str)
        assert result.endswith("test_file.txt")


@pytest.mark.asyncio
async def test_upload_file_404_error(mock_file):
    """Test handling of 404 error during upload."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"

    # Create a 404 error
    error = ClientResponseError(
        status=404,
        message="Not Found",
        request_info=MagicMock(),
        history=()
    )

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.upload = AsyncMock(side_effect=error)
        mock_session.return_value.__aenter__.return_value = mock_session

        # Should return filename without raising error
        result = await upload_file('my_bucket', path, mock_file, user_id)
        assert result.endswith("test_file.txt")


@pytest.mark.asyncio
async def test_upload_file_auth_error(mock_file):
    """Test handling of authentication error during upload."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"

    # Create an auth error
    error = ClientResponseError(
        status=400,
        message="invalid_grant",
        request_info=MagicMock(),
        history=()
    )

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.upload = AsyncMock(side_effect=error)
        mock_session.return_value.__aenter__.return_value = mock_session

        with pytest.raises(ServerError) as exc_info:
            await upload_file('my_bucket', path, mock_file, user_id)
        assert "Authentication error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_other_error(mock_file):
    """Test handling of other errors during upload."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"

    # Create a generic error
    error = Exception("Generic error")

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.upload = AsyncMock(side_effect=error)
        mock_session.return_value.__aenter__.return_value = mock_session

        with pytest.raises(StorageError) as exc_info:
            await upload_file('my_bucket', path, mock_file, user_id)
        assert "Failed to upload file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_file_success():
    """Test successful file deletion."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"
    file_name = "test_file.txt"

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.delete = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session

        # Should complete without error
        await delete_file('my_bucket', path, file_name, user_id)
        mock_storage.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file_404_error():
    """Test handling of 404 error during deletion."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"
    file_name = "test_file.txt"

    error = ClientResponseError(
        status=404,
        message="Not Found",
        request_info=MagicMock(),
        history=()
    )

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.delete = AsyncMock(side_effect=error)
        mock_session.return_value.__aenter__.return_value = mock_session

        # Should complete without error for 404
        await delete_file('my_bucket', path, file_name, user_id)


@pytest.mark.asyncio
async def test_delete_file_other_error():
    """Test handling of other errors during deletion."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    path = "test_path"
    file_name = "test_file.txt"

    error = Exception("Generic error")

    with patch('aiohttp.ClientSession') as mock_session, \
            patch('app.core.storage.Storage') as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.delete = AsyncMock(side_effect=error)
        mock_session.return_value.__aenter__.return_value = mock_session

        with pytest.raises(StorageError) as exc_info:
            await delete_file('my_bucket', path, file_name, user_id)
        assert "Failed to delete file" in str(exc_info.value)


def test_handle_gcs_error():
    """Test GCS error handling function."""
    file_path = "test/path/file.txt"

    # Test 404 error
    error_404 = ClientResponseError(
        status=404,
        message="Not Found",
        request_info=MagicMock(),
        history=()
    )
    handle_gcs_error(error_404, file_path)  # Should not raise

    # Test auth error
    error_auth = ClientResponseError(
        status=400,
        message="invalid_grant",
        request_info=MagicMock(),
        history=()
    )
    with pytest.raises(ServerError) as exc_info:
        handle_gcs_error(error_auth, file_path)
    assert "Authentication error" in str(exc_info.value)

    # Test other error
    error_other = ClientResponseError(
        status=500,
        message="Internal Server Error",
        request_info=MagicMock(),
        history=()
    )
    with pytest.raises(StorageError) as exc_info:
        handle_gcs_error(error_other, file_path)
    assert "GCS operation failed" in str(exc_info.value)
