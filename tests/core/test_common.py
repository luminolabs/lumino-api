import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select, Column, String
from sqlalchemy.exc import SQLAlchemyError

from app.core.common import paginate_query, parse_date, parse_datetime
from app.core.database import Base
from app.core.exceptions import BadRequestError


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.scalar.return_value = 10
    return db


# Test table setup
class TestModel(Base):
    __tablename__ = 'test_model'
    id = Column(String, primary_key=True)
    name = Column(String)


@pytest.fixture
def test_data():
    """Create test data."""
    return [
        TestModel(id=str(uuid.uuid4()), name=f"Test {i}")
        for i in range(1, 11)  # Create 10 test records
    ]


@pytest.mark.asyncio
async def test_paginate_query_valid_params(mock_db, test_data):
    """Test pagination with valid parameters."""
    # Setup mock database
    mock_db.execute.return_value.all.return_value = test_data[0:5]  # Return first 5 records
    mock_db.execute.return_value.scalar.return_value = 10  # Total count

    # Create query
    query = select(TestModel)

    # Test pagination
    items, pagination = await paginate_query(mock_db, query, page=1, items_per_page=5)

    assert len(items) == 5
    assert pagination.total_pages == 2
    assert pagination.current_page == 1
    assert pagination.items_per_page == 5


@pytest.mark.asyncio
async def test_paginate_query_last_page(mock_db, test_data):
    """Test pagination when accessing the last page."""
    # Setup mock database
    mock_db.execute.return_value.all.return_value = test_data[5:10]  # Return last 5 records
    mock_db.execute.return_value.scalar.return_value = 10  # Total count

    # Create query
    query = select(TestModel)

    # Test pagination
    items, pagination = await paginate_query(mock_db, query, page=2, items_per_page=5)

    assert len(items) == 5
    assert pagination.total_pages == 2
    assert pagination.current_page == 2
    assert pagination.items_per_page == 5


@pytest.mark.asyncio
async def test_paginate_query_empty_page(mock_db):
    """Test pagination when accessing an empty page."""
    # Setup mock database
    mock_db.execute.return_value.all.return_value = []
    mock_db.execute.return_value.scalar.return_value = 10  # Total count

    # Create query
    query = select(TestModel)

    # Test pagination
    items, pagination = await paginate_query(mock_db, query, page=3, items_per_page=5)

    assert len(items) == 0
    assert pagination.total_pages == 2
    assert pagination.current_page == 3
    assert pagination.items_per_page == 5


@pytest.mark.asyncio
async def test_paginate_query_invalid_page(mock_db):
    """Test pagination with invalid page number."""
    # Create query
    query = select(TestModel)

    # Test with invalid page number
    with pytest.raises(BadRequestError):
        await paginate_query(mock_db, query, page=0, items_per_page=5)


@pytest.mark.asyncio
async def test_paginate_query_invalid_items_per_page(mock_db):
    """Test pagination with invalid items per page."""
    # Create query
    query = select(TestModel)

    # Test with invalid items per page
    with pytest.raises(BadRequestError):
        await paginate_query(mock_db, query, page=1, items_per_page=0)


@pytest.mark.asyncio
async def test_paginate_query_database_error(mock_db):
    """Test pagination when database error occurs."""
    # Setup mock database to raise error
    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    # Create query
    query = select(TestModel)

    # Test database error
    with pytest.raises(SQLAlchemyError):
        await paginate_query(mock_db, query, page=1, items_per_page=5)


def test_parse_date_valid():
    """Test parsing valid date string."""
    result = parse_date("2024-01-01")
    assert isinstance(result, date)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1


def test_parse_date_invalid_format():
    """Test parsing invalid date format."""
    with pytest.raises(BadRequestError):
        parse_date("01-01-2024")  # Wrong format


def test_parse_date_invalid_date():
    """Test parsing invalid date."""
    with pytest.raises(BadRequestError):
        parse_date("2024-13-01")  # Invalid month


def test_parse_date_none():
    """Test parsing None date."""
    result = parse_date(None)
    assert result is None


def test_parse_datetime_valid():
    """Test parsing valid datetime string."""
    result = parse_datetime("2024-01-01T12:00:00Z")
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0
    assert result.second == 0


def test_parse_datetime_invalid_format():
    """Test parsing invalid datetime format."""
    with pytest.raises(BadRequestError):
        parse_datetime("2024-01-01 12:00:00")  # Wrong format


def test_parse_datetime_invalid_datetime():
    """Test parsing invalid datetime."""
    with pytest.raises(BadRequestError):
        parse_datetime("2024-13-01T12:00:00Z")  # Invalid month


def test_parse_datetime_none():
    """Test parsing None datetime."""
    result = parse_datetime(None)
    assert result is None
