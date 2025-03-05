from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.exceptions import BadRequestError, NotFoundError, ForbiddenError
from app.models.whitelist import Whitelist
from app.schemas.whitelist import WhitelistRequestCreate
from app.services.whitelist import create_whitelist_request, get_whitelist_request, update_whitelist_status


@pytest.fixture
def mock_whitelist_request():
    """Create a mock whitelist request object."""
    whitelist = MagicMock(spec=Whitelist)
    whitelist.id = UUID('12345678-1234-5678-1234-567812345678')
    whitelist.user_id = UUID('87654321-8765-4321-8765-432187654321')
    whitelist.name = "Test User"
    whitelist.email = "test@example.com"
    whitelist.phone_number = "1234567890"
    whitelist.is_whitelisted = False
    whitelist.has_signed_nda = False
    return whitelist


@pytest.mark.asyncio
async def test_create_whitelist_request_success(mock_db, mock_whitelist_request):
    """Test successful creation of a whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create request data
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        request_data = WhitelistRequestCreate(
            name="Test User",
            email="test@example.com",
            phone_number="1234567890"
        )
        
        # Mock the db.add behavior to set our mock_whitelist_request
        def mock_add(obj):
            for key, value in request_data.dict().items():
                setattr(mock_whitelist_request, key, value)
            setattr(mock_whitelist_request, 'user_id', user_id)
        mock_db.add = MagicMock(side_effect=mock_add)
        
        # Call function with context manager to handle model_config
        with patch('app.services.whitelist.Whitelist', return_value=mock_whitelist_request):
            result = await create_whitelist_request(mock_db, user_id, request_data)
            
            # Verify results
            assert result.name == request_data.name
            assert result.email == request_data.email
            assert result.phone_number == request_data.phone_number
            assert result.is_whitelisted is False
            assert result.has_signed_nda is False
            assert result.user_id == user_id
            
            # Verify query calls
            mock_queries.get_whitelist_by_user_id.assert_awaited_once_with(mock_db, user_id)
            mock_db.commit.assert_awaited_once()
            mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_whitelist_request_duplicate(mock_db, mock_whitelist_request):
    """Test attempt to create duplicate whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=mock_whitelist_request)
        
        # Create request data
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        request_data = WhitelistRequestCreate(
            name="Test User",
            email="test@example.com",
            phone_number="1234567890"
        )
        
        # Call function and expect error
        with pytest.raises(BadRequestError) as exc_info:
            await create_whitelist_request(mock_db, user_id, request_data)
        
        assert f"User {user_id} already has a whitelist request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_whitelist_request_success(mock_db, mock_whitelist_request):
    """Test successful retrieval of whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=mock_whitelist_request)
        
        # User requesting their own whitelist
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        
        # Call function
        result = await get_whitelist_request(mock_db, user_id, user_id, False)
        
        # Verify results
        assert result.name == mock_whitelist_request.name
        assert result.email == mock_whitelist_request.email
        assert result.user_id == user_id
        
        # Verify query calls
        mock_queries.get_whitelist_by_user_id.assert_awaited_once_with(mock_db, user_id)


@pytest.mark.asyncio
async def test_get_whitelist_request_admin_access(mock_db, mock_whitelist_request):
    """Test admin accessing another user's whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=mock_whitelist_request)
        
        # Target user and admin user
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        admin_id = UUID('11111111-1111-1111-1111-111111111111')
        
        # Call function with admin flag
        result = await get_whitelist_request(mock_db, user_id, admin_id, True)
        
        # Verify results
        assert result.user_id == user_id
        
        # Verify query calls
        mock_queries.get_whitelist_by_user_id.assert_awaited_once_with(mock_db, user_id)


@pytest.mark.asyncio
async def test_get_whitelist_request_unauthorized(mock_db, mock_whitelist_request):
    """Test unauthorized access to whitelist request."""
    # Target user and different non-admin user
    user_id = UUID('87654321-8765-4321-8765-432187654321')
    other_user_id = UUID('22222222-2222-2222-2222-222222222222')
    
    # Call function and expect error
    with pytest.raises(ForbiddenError) as exc_info:
        await get_whitelist_request(mock_db, user_id, other_user_id, False)
    
    assert "You don't have permission to view this whitelist request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_whitelist_request_not_found(mock_db):
    """Test retrieving non-existent whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=None)
        
        # User ID
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        
        # Call function and expect error
        with pytest.raises(NotFoundError) as exc_info:
            await get_whitelist_request(mock_db, user_id, user_id, False)
        
        assert f"Whitelist request not found for user: {user_id}" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_whitelist_status_success(mock_db, mock_whitelist_request):
    """Test successful update of whitelist status."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=mock_whitelist_request)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # User ID
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        
        # Update data - only change is_whitelisted
        update_data = MagicMock()
        update_data.dict = MagicMock(return_value={"is_whitelisted": True})
        
        # Call function
        result = await update_whitelist_status(mock_db, user_id, update_data)
        
        # Verify model was updated
        assert mock_whitelist_request.is_whitelisted is True
        
        # Verify db operations
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_whitelist_request)
        
        # Verify query calls
        mock_queries.get_whitelist_by_user_id.assert_awaited_once_with(mock_db, user_id)


@pytest.mark.asyncio
async def test_update_nda_status_success(mock_db, mock_whitelist_request):
    """Test successful update of NDA status."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=mock_whitelist_request)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # User ID
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        
        # Update data - only change has_signed_nda
        update_data = MagicMock()
        update_data.dict = MagicMock(return_value={"has_signed_nda": True})
        
        # Call function
        result = await update_whitelist_status(mock_db, user_id, update_data)
        
        # Verify model was updated
        assert mock_whitelist_request.has_signed_nda is True
        
        # Verify db operations
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_whitelist_request)


@pytest.mark.asyncio
async def test_update_whitelist_status_not_found(mock_db):
    """Test updating non-existent whitelist request."""
    with patch('app.services.whitelist.whitelist_queries') as mock_queries:
        # Configure mocks
        mock_queries.get_whitelist_by_user_id = AsyncMock(return_value=None)
        
        # User ID
        user_id = UUID('87654321-8765-4321-8765-432187654321')
        
        # Update data
        update_data = MagicMock()
        update_data.dict = MagicMock(return_value={"is_whitelisted": True})
        
        # Call function and expect error
        with pytest.raises(NotFoundError) as exc_info:
            await update_whitelist_status(mock_db, user_id, update_data)
        
        assert f"Whitelist request not found for user: {user_id}" in str(exc_info.value)