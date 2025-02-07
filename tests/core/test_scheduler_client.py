from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from aiohttp import ClientSession

from app.core.constants import FineTuningJobStatus
from app.core.exceptions import (
    FineTuningJobCreationError,
    FineTuningJobRefreshError,
    FineTuningJobCancellationError
)
from app.core.scheduler_client import (
    start_fine_tuning_job,
    fetch_job_details,
    stop_fine_tuning_job
)


@pytest.fixture
def mock_job():
    """Create a mock fine-tuning job."""
    job = MagicMock()
    job.id = UUID('12345678-1234-5678-1234-567812345678')
    job.user_id = UUID('98765432-9876-5432-9876-987654321098')
    job.provider = MagicMock(value='GCP')
    job.status = FineTuningJobStatus.NEW
    return job


@pytest.fixture
def mock_dataset():
    """Create a mock dataset."""
    dataset = MagicMock()
    dataset.file_name = "test_dataset.jsonl"
    return dataset


@pytest.fixture
def mock_base_model():
    """Create a mock base model."""
    base_model = MagicMock()
    base_model.name = "test_model"
    base_model.cluster_config = {
        "lora": {
            "num_gpus": 1,
            "gpu_type": "test-gpu"
        },
        "qlora": {
            "num_gpus": 1,
            "gpu_type": "test-gpu"
        },
        "full": {
            "num_gpus": 2,
            "gpu_type": "test-gpu"
        }
    }
    return base_model


@pytest.fixture
def mock_job_detail():
    """Create a mock job detail."""
    detail = MagicMock()
    detail.parameters = {
        "batch_size": 2,
        "shuffle": True,
        "num_epochs": 1,
        "use_lora": True,
        "use_qlora": False
    }
    return detail


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = UUID('98765432-9876-5432-9876-987654321098')
    return user


@pytest.mark.asyncio
async def test_start_fine_tuning_job_success(
        mock_db,
        mock_job,
        mock_dataset,
        mock_base_model,
        mock_job_detail,
        mock_user
):
    """Test successful job start."""
    # Mock the job query
    with patch('app.core.scheduler_client.ft_queries.get_job_with_details_full') as mock_query:
        mock_query.return_value = (mock_job, mock_dataset, mock_base_model, mock_job_detail)

        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call the function
            await start_fine_tuning_job(mock_db, mock_job.id, mock_user.id)

            # Verify the scheduler API was called correctly
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "jobs/gcp" in call_args[0][0]

            # Verify payload structure
            payload = call_args[1]['json']
            assert payload['job_id'] == str(mock_job.id)
            assert payload['workflow'] == 'torchtunewrapper'
            assert 'args' in payload
            assert payload['gpu_type'] == 'test-gpu'
            assert payload['num_gpus'] == 1


@pytest.mark.asyncio
async def test_start_fine_tuning_job_validation_error(mock_db, mock_job):
    """Test job start with validation error."""
    # Mock the job query
    with patch('app.core.scheduler_client.ft_queries.get_job_with_details_full') as mock_query:
        mock_query.return_value = None

        with pytest.raises(FineTuningJobCreationError) as exc_info:
            await start_fine_tuning_job(mock_db, mock_job.id, mock_job.user_id)

        assert "Failed to find job" in str(exc_info.value)


@pytest.mark.asyncio
async def test_start_fine_tuning_job_scheduler_error(
        mock_db,
        mock_job,
        mock_dataset,
        mock_base_model,
        mock_job_detail,
        mock_user
):
    """Test job start with scheduler error."""
    # Mock the job query
    with patch('app.core.scheduler_client.ft_queries.get_job_with_details_full') as mock_query:
        mock_query.return_value = (mock_job, mock_dataset, mock_base_model, mock_job_detail)

        # Mock aiohttp session with error response
        mock_response = AsyncMock()
        mock_response.status = 422
        mock_response.json = AsyncMock(return_value={"message": "Validation error"})
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(FineTuningJobCreationError) as exc_info:
                await start_fine_tuning_job(mock_db, mock_job.id, mock_user.id)

            assert "Validation error" in str(exc_info.value)

# Add test for full fine-tuning disabled
@pytest.mark.asyncio
async def test_start_fine_tuning_job_full_disabled(
        mock_db,
        mock_job,
        mock_dataset,
        mock_base_model,
        mock_job_detail,
        mock_user
):
    """Test that full fine-tuning is disabled."""
    # Modify mock_job_detail to attempt full fine-tuning
    mock_job_detail.parameters = {
        "batch_size": 2,
        "shuffle": True,
        "num_epochs": 1,
        "use_lora": False,
        "use_qlora": False
    }

    # Mock the job query
    with patch('app.core.scheduler_client.ft_queries.get_job_with_details_full') as mock_query:
        mock_query.return_value = (mock_job, mock_dataset, mock_base_model, mock_job_detail)

        # Verify that attempting full fine-tuning raises an error
        with pytest.raises(FineTuningJobCreationError) as exc_info:
            await start_fine_tuning_job(mock_db, mock_job.id, mock_user.id)

        assert "Full fine-tuning is currently disabled" in str(exc_info.value)

@pytest.mark.asyncio
async def test_fetch_job_details_success():
    """Test successful job details fetch."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    job_ids = [UUID('12345678-1234-5678-1234-567812345678')]
    expected_response = [{"job_id": str(job_ids[0]), "status": "RUNNING"}]

    # Mock aiohttp session
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=expected_response)
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await fetch_job_details(user_id, job_ids)
        assert result == expected_response

        # Verify correct API call
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "jobs/get_by_user_and_ids" in call_args[0][0]

        # Verify payload
        payload = call_args[1]['json']
        assert payload['user_id'] == str(user_id)
        assert payload['job_ids'] == [str(job_ids[0])]


@pytest.mark.asyncio
async def test_fetch_job_details_error():
    """Test job details fetch with error."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    job_ids = [UUID('12345678-1234-5678-1234-567812345678')]

    # Mock aiohttp session with error
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal server error")
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        with pytest.raises(FineTuningJobRefreshError) as exc_info:
            await fetch_job_details(user_id, job_ids)

        assert "Error refreshing job statuses" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_fine_tuning_job_success():
    """Test successful job stop."""
    job_id = UUID('12345678-1234-5678-1234-567812345678')
    user_id = UUID('98765432-9876-5432-9876-987654321098')

    # Mock aiohttp session
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"status": "stopping"})
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await stop_fine_tuning_job(job_id, user_id)
        assert result == {"status": "stopping"}

        # Verify correct API call
        mock_session.post.assert_called_once()
        assert f"jobs/gcp/stop/{job_id}/{user_id}" in mock_session.post.call_args[0][0]


@pytest.mark.asyncio
async def test_stop_fine_tuning_job_not_found():
    """Test job stop when job not found."""
    job_id = UUID('12345678-1234-5678-1234-567812345678')
    user_id = UUID('98765432-9876-5432-9876-987654321098')

    # Mock aiohttp session with not found error
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.text = AsyncMock(return_value="Job not found")
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        with pytest.raises(FineTuningJobCancellationError) as exc_info:
            await stop_fine_tuning_job(job_id, user_id)

        assert "Job not found or not running" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_fine_tuning_job_error():
    """Test job stop with error."""
    job_id = UUID('12345678-1234-5678-1234-567812345678')
    user_id = UUID('98765432-9876-5432-9876-987654321098')

    # Mock aiohttp session with error
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal server error")
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        with pytest.raises(FineTuningJobCancellationError) as exc_info:
            await stop_fine_tuning_job(job_id, user_id)

        assert "Failed to stop job" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scheduler_disabled(mock_db):
    """Test behavior when scheduler is disabled."""
    with patch('app.core.scheduler_client.config.run_with_scheduler', False):
        # All functions should return early without error
        job_id = UUID('12345678-1234-5678-1234-567812345678')
        user_id = UUID('98765432-9876-5432-9876-987654321098')

        await start_fine_tuning_job(mock_db, job_id, user_id)
        assert await fetch_job_details(user_id, [job_id]) == []
        assert await stop_fine_tuning_job(job_id, user_id) is None
