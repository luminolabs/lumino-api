from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.constants import UsageUnit, ServiceName
from app.core.exceptions import BadRequestError
from app.models.fine_tuning_job import FineTuningJob
from app.models.usage import Usage
from app.services.usage import get_usage_records, get_total_cost


@pytest.fixture
def mock_usage_record():
    """Create a mock usage record."""
    usage = MagicMock(spec=Usage)
    usage.id = UUID('12345678-1234-5678-1234-567812345678')
    usage.created_at = datetime.utcnow()
    usage.user_id = UUID('98765432-9876-5432-9876-987654321098')
    usage.usage_amount = 1000000
    usage.cost = 10.0
    usage.service_name = ServiceName.FINE_TUNING_JOB
    usage.usage_unit = UsageUnit.TOKEN
    return usage


@pytest.fixture
def mock_job():
    """Create a mock fine-tuning job."""
    job = MagicMock(spec=FineTuningJob)
    job.name = "test-job"
    return job


@pytest.mark.asyncio
async def test_get_usage_records_success(mock_db, mock_usage_record, mock_job):
    """Test successful retrieval of usage records."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    with patch('app.services.usage.usage_queries') as mock_queries:
        # Configure mocks
        mock_queries.count_usage_records = AsyncMock(return_value=1)
        mock_queries.get_usage_records = AsyncMock(
            return_value=[(mock_usage_record, mock_job.name)]
        )

        # Call function
        result, pagination = await get_usage_records(
            mock_db,
            user_id,
            start_date,
            end_date
        )

        # Verify results
        assert len(result) == 1
        record = result[0]
        assert record.id == mock_usage_record.id
        assert record.usage_amount == mock_usage_record.usage_amount
        assert record.cost == mock_usage_record.cost
        assert record.fine_tuning_job_name == mock_job.name

        # Verify pagination
        assert pagination.total_pages == 1
        assert pagination.current_page == 1
        assert pagination.items_per_page == 20

        # Verify query calls with correct date parsing
        mock_queries.count_usage_records.assert_awaited_once_with(
            mock_db,
            user_id,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        mock_queries.get_usage_records.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_usage_records_invalid_dates(mock_db):
    """Test usage records retrieval with invalid dates."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')

    # Test invalid date format
    with pytest.raises(BadRequestError):
        await get_usage_records(
            mock_db,
            user_id,
            "invalid-date",
            "2024-01-31"
        )

    # Test end date before start date
    with pytest.raises(BadRequestError):
        await get_usage_records(
            mock_db,
            user_id,
            "2024-01-31",
            "2024-01-01"
        )


@pytest.mark.asyncio
async def test_get_total_cost_success(mock_db):
    """Test successful retrieval of total cost."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    with patch('app.services.usage.usage_queries') as mock_queries:
        # Configure mock
        mock_queries.get_total_cost = AsyncMock(return_value=100.0)

        # Call function
        result = await get_total_cost(mock_db, user_id, start_date, end_date)

        # Verify results
        assert result.total_cost == 100.0
        assert result.start_date == date(2024, 1, 1)
        assert result.end_date == date(2024, 1, 31)

        # Verify query call with correct date parsing
        mock_queries.get_total_cost.assert_awaited_once_with(
            mock_db,
            user_id,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )


@pytest.mark.asyncio
async def test_get_total_cost_invalid_dates(mock_db):
    """Test total cost retrieval with invalid dates."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')

    # Test invalid date format
    with pytest.raises(BadRequestError):
        await get_total_cost(
            mock_db,
            user_id,
            "invalid-date",
            "2024-01-31"
        )

    # Test end date before start date
    with pytest.raises(BadRequestError):
        await get_total_cost(
            mock_db,
            user_id,
            "2024-01-31",
            "2024-01-01"
        )


@pytest.mark.asyncio
async def test_get_usage_records_empty(mock_db):
    """Test retrieving empty usage records list."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    with patch('app.services.usage.usage_queries') as mock_queries:
        # Configure mocks for empty results
        mock_queries.count_usage_records = AsyncMock(return_value=0)
        mock_queries.get_usage_records = AsyncMock(return_value=[])

        # Call function
        result, pagination = await get_usage_records(
            mock_db,
            user_id,
            start_date,
            end_date
        )

        # Verify empty results
        assert len(result) == 0
        assert pagination.total_pages == 0
        assert pagination.current_page == 1
        assert pagination.items_per_page == 20


@pytest.mark.asyncio
async def test_get_usage_records_pagination(mock_db, mock_usage_record, mock_job):
    """Test usage records pagination."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    with patch('app.services.usage.usage_queries') as mock_queries:
        # Configure mocks for second page
        mock_queries.count_usage_records = AsyncMock(return_value=25)
        mock_queries.get_usage_records = AsyncMock(
            return_value=[(mock_usage_record, mock_job.name)]
        )

        # Call function with page 2
        result, pagination = await get_usage_records(
            mock_db,
            user_id,
            start_date,
            end_date,
            page=2,
            items_per_page=10
        )

        # Verify pagination
        assert pagination.total_pages == 3
        assert pagination.current_page == 2
        assert pagination.items_per_page == 10

        # Verify correct offset in query
        mock_queries.get_usage_records.assert_awaited_once_with(
            mock_db,
            user_id,
            date(2024, 1, 1),
            date(2024, 1, 31),
            10,  # offset
            10  # limit
        )
