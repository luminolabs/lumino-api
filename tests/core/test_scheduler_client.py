import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from aiohttp import ClientSession, ClientResponse, ClientResponseError

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

from app.models.base_model import BaseModel
from app.models.user import User
from app.models.dataset import Dataset
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail

# These are actually needed for model relationships
from app.models.api_key import ApiKey
from app.models.billing_credit import BillingCredit
from app.models.fine_tuned_model import FineTunedModel
from app.models.usage import Usage


@pytest.fixture
def mock_response():
    """Create a properly mocked aiohttp ClientResponse."""
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Success")
    response.json = AsyncMock(return_value={"status": "success"})
    # Add async context manager methods
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response

@pytest.fixture
def mock_session(mock_response):
    """Create a properly mocked aiohttp ClientSession."""
    session = AsyncMock()

    # Create a proper async context manager for post()
    async def mock_post(*args, **kwargs):
        return mock_response

    session.post = mock_post
    # Add async context manager methods
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_job_data():
    """Create mock job data."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    base_model = BaseModel(
        id=uuid.uuid4(),
        name="test_model",
        cluster_config={
            "lora": {"num_gpus": 1, "gpu_type": "test-gpu"},
            "qlora": {"num_gpus": 1, "gpu_type": "test-gpu"},
            "full": {"num_gpus": 2, "gpu_type": "test-gpu"}
        }
    )
    dataset = Dataset(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="test_dataset.jsonl"
    )
    user = User(id=user_id)
    job = FineTuningJob(
        id=job_id,
        user_id=user_id,
        base_model_id=base_model.id,
        dataset_id=dataset.id,
        status=FineTuningJobStatus.NEW,
        provider="GCP"
    )
    job_detail = FineTuningJobDetail(
        fine_tuning_job_id=job_id,
        parameters={
            "batch_size": 2,
            "shuffle": True,
            "num_epochs": 1,
            "use_lora": True,
            "use_qlora": False
        }
    )
    return job, dataset, base_model, job_detail, user


@pytest.mark.asyncio
async def test_start_fine_tuning_job_success(mock_job_data, mock_session, mock_response):
    """Test successful start of fine-tuning job."""
    job, dataset, base_model, job_detail, user = mock_job_data

    # Mock DB session
    mock_db = AsyncMock()
    mock_db.execute.return_value.first.return_value = (job, dataset, base_model, job_detail, user)

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session):
        await start_fine_tuning_job(job.id)

    # Verify the correct payload was sent
    expected_payload = {
        'job_id': str(job.id),
        'workflow': 'torchtunewrapper',
        'args': {
            'job_config_name': base_model.name,
            'dataset_id': f'gs://test-bucket/datasets/{user.id}/{dataset.file_name}',
            'batch_size': 2,
            'shuffle': True,
            'num_epochs': 1,
            'use_lora': True,
            'use_qlora': False,
            'num_gpus': 1
        },
        'gpu_type': 'test-gpu',
        'num_gpus': 1,
        'user_id': str(user.id),
        'keep_alive': False
    }

    _, kwargs = mock_session.post.call_args
    assert kwargs['json'] == expected_payload


@pytest.mark.asyncio
async def test_fetch_job_details_success(mock_session, mock_response):
    """Test successful fetching of job details."""
    user_id = uuid.uuid4()
    job_ids = [uuid.uuid4(), uuid.uuid4()]
    expected_response = [
        {'job_id': str(job_ids[0]), 'status': 'RUNNING'},
        {'job_id': str(job_ids[1]), 'status': 'COMPLETED'}
    ]

    mock_response.json.return_value = expected_response

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session):
        result = await fetch_job_details(user_id, job_ids)

    assert result == expected_response


@pytest.mark.asyncio
async def test_start_fine_tuning_job_validation_error(mock_job_data, mock_session, mock_response):
    """Test handling of validation error when starting fine-tuning job."""
    job, dataset, base_model, job_detail, user = mock_job_data

    # Mock DB session
    mock_db = AsyncMock()
    mock_db.execute.return_value.first.return_value = (job, dataset, base_model, job_detail, user)
    mock_db.get.return_value = job

    # Configure mock response for validation error
    mock_response.status = 422
    mock_response.json.return_value = {'message': 'Validation error'}

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session), \
            pytest.raises(FineTuningJobCreationError) as exc_info:
        await start_fine_tuning_job(job.id)

    assert 'Validation error' in str(exc_info.value)
    assert job.status == FineTuningJobStatus.FAILED


@pytest.mark.asyncio
async def test_fetch_job_details_error(mock_session, mock_response):
    """Test error handling when fetching job details."""
    user_id = uuid.uuid4()
    job_ids = [uuid.uuid4()]

    # Configure mock response for error
    mock_response.status = 500
    mock_response.text.return_value = "Internal server error"

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session), \
            pytest.raises(FineTuningJobRefreshError) as exc_info:
        await fetch_job_details(user_id, job_ids)

    assert "Internal server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_fine_tuning_job_success(mock_session, mock_response):
    """Test successful stopping of fine-tuning job."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    expected_response = {'status': 'stopped'}

    mock_response.json.return_value = expected_response

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session):
        result = await stop_fine_tuning_job(job_id, user_id)

    assert result == expected_response


@pytest.mark.asyncio
async def test_stop_fine_tuning_job_not_found(mock_session, mock_response):
    """Test handling of not found error when stopping fine-tuning job."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Configure mock response for not found
    mock_response.status = 404
    mock_response.text.return_value = "Job not found"

    with patch('app.core.scheduler_client.ClientSession', return_value=mock_session), \
            pytest.raises(FineTuningJobCancellationError) as exc_info:
        await stop_fine_tuning_job(job_id, user_id)

    assert "Job not found or not running" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scheduler_disabled():
    """Test behavior when scheduler is disabled."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with patch('app.core.scheduler_client.config.run_with_scheduler', False):
        # All functions should return without making any requests
        assert await start_fine_tuning_job(job_id) is None
        assert await fetch_job_details(user_id, [job_id]) == []
        assert await stop_fine_tuning_job(job_id, user_id) is None


@pytest.mark.asyncio
async def test_start_fine_tuning_job_with_qlora(mock_job_data, mock_session, mock_response):
    """Test starting a fine-tuning job with QLORA parameters."""
    job, dataset, base_model, job_detail, user = mock_job_data
    job_detail.parameters['use_qlora'] = True

    # Create a mock query result class
    class MockQueryResult:
        def first(self):
            return (job, dataset, base_model, job_detail, user)

        def scalar_one_or_none(self):
            return job

    # Mock DB session with proper execute() return value
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockQueryResult())
    mock_db.get = AsyncMock(return_value=job)
    mock_db.commit = AsyncMock()

    # Use patches to prevent network calls and provide mock db
    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('app.core.scheduler_client.config.scheduler_zen_url', 'http://mock-url'), \
            patch('app.core.scheduler_client.AsyncSessionLocal', return_value=mock_db):
        await start_fine_tuning_job(job.id)

    # Verify DB was queried with correct parameters
    assert mock_db.execute.called

    # Verify the HTTP call payload
    assert mock_session.post.called
    args, kwargs = mock_session.post.call_args
    assert 'json' in kwargs
    payload = kwargs['json']

    # Verify QLORA configuration
    assert payload['args']['use_qlora'] is True
    assert payload['args']['use_lora'] is True
    assert payload['args']['num_gpus'] == 1
    assert payload['gpu_type'] == 'test-gpu'
    assert payload['workflow'] == 'torchtunewrapper'

    # Verify job and user IDs
    assert payload['job_id'] == str(job.id)
    assert payload['user_id'] == str(user.id)

    # Verify job parameters
    job_args = payload['args']
    assert job_args['batch_size'] == 2
    assert job_args['shuffle'] is True
    assert job_args['num_epochs'] == 1
    assert job_args['job_config_name'] == base_model.name
    assert job_args['dataset_id'] == f'gs://test-bucket/datasets/{user.id}/{dataset.file_name}'