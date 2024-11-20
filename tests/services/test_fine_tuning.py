from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.constants import (
    FineTuningJobStatus,
    FineTuningJobType,
    ComputeProvider,
    UserStatus,
    DatasetStatus,
    BaseModelStatus,
    FineTunedModelStatus
)
from app.core.exceptions import (
    ForbiddenError,
    FineTuningJobNotFoundError,
    BadRequestError
)
from app.models.base_model import BaseModel
from app.models.dataset import Dataset
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.user import User
from app.queries.common import make_naive, now_utc
from app.schemas.fine_tuning import FineTuningJobCreate
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    cancel_fine_tuning_job,
    delete_fine_tuning_job,
    update_job_progress,
    get_jobs_for_status_update,
)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = UUID('12345678-1234-5678-1234-567812345678')
    user.email = "test@example.com"
    user.status = UserStatus.ACTIVE
    user.email_verified = True
    user.credits_balance = 100.0
    return user

@pytest.fixture
def mock_base_model():
    """Create a mock base model."""
    model = MagicMock(spec=BaseModel)
    model.id = UUID('23456789-2345-6789-2345-678923456789')
    model.name = "llm_llama3_1_8b"
    model.status = BaseModelStatus.ACTIVE
    return model

@pytest.fixture
def mock_dataset():
    """Create a mock dataset."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = UUID('34567890-3456-7890-3456-789034567890')
    dataset.name = "test-dataset"
    dataset.status = DatasetStatus.VALIDATED
    return dataset

@pytest.fixture
def mock_job():
    """Create a mock fine-tuning job."""
    job = MagicMock(spec=FineTuningJob)
    job.id = UUID('45678901-4567-8901-4567-890145678901')
    job.created_at = make_naive(now_utc())
    job.updated_at = make_naive(now_utc())
    job.name = "test-job"
    job.type = FineTuningJobType.LORA
    job.provider = ComputeProvider.GCP
    job.status = FineTuningJobStatus.NEW
    return job

@pytest.fixture
def mock_job_detail():
    """Create a mock job detail."""
    detail = MagicMock(spec=FineTuningJobDetail)
    detail.parameters = {
        "batch_size": 2,
        "shuffle": True,
        "num_epochs": 1,
    }
    detail.metrics = {}
    detail.timestamps = {}
    return detail

@pytest.mark.asyncio
async def test_create_fine_tuning_job_success(
        mock_db, mock_user, mock_base_model, mock_dataset):
    """Test successful fine-tuning job creation."""
    job_create = FineTuningJobCreate(
        base_model_name="llm_llama3_1_8b",
        dataset_name="test-dataset",
        name="test-job",
        type=FineTuningJobType.LORA,
        provider=ComputeProvider.GCP,
        parameters={"batch_size": 2}
    )

    with patch('app.services.fine_tuning.model_queries') as mock_model_queries, \
            patch('app.services.fine_tuning.dataset_queries') as mock_dataset_queries, \
            patch('app.services.fine_tuning.ft_queries') as mock_ft_queries, \
            patch('app.services.fine_tuning.start_fine_tuning_job') as mock_start_job:

        # Configure mocks
        mock_model_queries.get_base_model_by_name = AsyncMock(return_value=mock_base_model)
        mock_dataset_queries.get_dataset_by_name = AsyncMock(return_value=mock_dataset)
        mock_ft_queries.get_job_with_details = AsyncMock(return_value=None)
        mock_start_job.return_value = None

        result = await create_fine_tuning_job(mock_db, mock_user, job_create)

        assert result.name == "test-job"
        assert result.type == FineTuningJobType.LORA
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()
        mock_start_job.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_fine_tuning_job_unverified_email(mock_db, mock_user, mock_base_model):
    """Test job creation with unverified email."""
    mock_user.email_verified = False
    job_create = FineTuningJobCreate(
        base_model_name="llm_llama3_1_8b",
        dataset_name="test-dataset",
        name="test-job",
        type=FineTuningJobType.LORA,
        provider=ComputeProvider.GCP,
        parameters={"batch_size": 2}
    )

    with pytest.raises(ForbiddenError):
        await create_fine_tuning_job(mock_db, mock_user, job_create)

@pytest.mark.asyncio
async def test_create_fine_tuning_job_insufficient_credits(mock_db, mock_user, mock_base_model):
    """Test job creation with insufficient credits."""
    mock_user.credits_balance = 0
    job_create = FineTuningJobCreate(
        base_model_name="llm_llama3_1_8b",
        dataset_name="test-dataset",
        name="test-job",
        type=FineTuningJobType.LORA,
        provider=ComputeProvider.GCP,
        parameters={"batch_size": 2}
    )

    with pytest.raises(ForbiddenError):
        await create_fine_tuning_job(mock_db, mock_user, job_create)

@pytest.mark.asyncio
async def test_get_fine_tuning_jobs(mock_db, mock_job):
    """Test retrieving fine-tuning jobs list."""
    with patch('app.services.fine_tuning.ft_queries') as mock_queries:
        mock_queries.count_jobs = AsyncMock(return_value=1)
        mock_queries.list_jobs = AsyncMock(
            return_value=[(mock_job, "llm_llama3_1_8b", "test-dataset")]
        )

        result, pagination = await get_fine_tuning_jobs(
            mock_db,
            UUID('12345678-1234-5678-1234-567812345678')
        )

        assert len(result) == 1
        assert result[0].name == mock_job.name
        assert pagination.total_pages == 1
        assert pagination.current_page == 1

@pytest.mark.asyncio
async def test_get_fine_tuning_job_success(mock_db, mock_job, mock_job_detail):
    """Test retrieving a specific fine-tuning job."""
    with patch('app.services.fine_tuning.ft_queries') as mock_queries:
        mock_queries.get_job_with_details = AsyncMock(
            return_value=(mock_job, mock_job_detail, "llm_llama3_1_8b", "test-dataset")
        )

        result = await get_fine_tuning_job(
            mock_db,
            UUID('12345678-1234-5678-1234-567812345678'),
            "test-job"
        )

        assert result.name == mock_job.name
        assert result.base_model_name == "llm_llama3_1_8b"
        assert result.dataset_name == "test-dataset"

@pytest.mark.asyncio
async def test_get_fine_tuning_job_not_found(mock_db):
    """Test retrieving a non-existent fine-tuning job."""
    with patch('app.services.fine_tuning.ft_queries') as mock_queries:
        mock_queries.get_job_with_details = AsyncMock(return_value=None)

        with pytest.raises(FineTuningJobNotFoundError):
            await get_fine_tuning_job(
                mock_db,
                UUID('12345678-1234-5678-1234-567812345678'),
                "nonexistent-job"
            )

@pytest.mark.asyncio
async def test_cancel_fine_tuning_job_success(mock_db, mock_job, mock_job_detail):
    """Test successful job cancellation."""
    mock_job.status = FineTuningJobStatus.RUNNING

    with patch('app.services.fine_tuning.ft_queries') as mock_queries, \
            patch('app.services.fine_tuning.stop_fine_tuning_job') as mock_stop:
        mock_queries.get_job_with_details = AsyncMock(
            return_value=(mock_job, mock_job_detail, "llm_llama3_1_8b", "test-dataset")
        )
        mock_stop.return_value = None

        result = await cancel_fine_tuning_job(
            mock_db,
            UUID('12345678-1234-5678-1234-567812345678'),
            "test-job"
        )

        assert result.status == FineTuningJobStatus.STOPPING
        mock_stop.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_cancel_fine_tuning_job_invalid_status(mock_db, mock_job, mock_job_detail):
    """Test cancelling a job with invalid status."""
    mock_job.status = FineTuningJobStatus.COMPLETED

    with patch('app.services.fine_tuning.ft_queries') as mock_queries:
        mock_queries.get_job_with_details = AsyncMock(
            return_value=(mock_job, mock_job_detail, "llm_llama3_1_8b", "test-dataset")
        )

        with pytest.raises(BadRequestError):
            await cancel_fine_tuning_job(
                mock_db,
                UUID('12345678-1234-5678-1234-567812345678'),
                "test-job"
            )

@pytest.mark.asyncio
async def test_delete_fine_tuning_job_success(mock_db, mock_job, mock_job_detail):
    """Test successful job deletion."""
    mock_model = MagicMock(spec=FineTunedModel)
    mock_model.status = FineTunedModelStatus.ACTIVE

    with patch('app.services.fine_tuning.ft_queries') as mock_ft_queries, \
            patch('app.services.fine_tuning.ft_models_queries') as mock_model_queries:
        mock_ft_queries.get_job_with_details = AsyncMock(
            return_value=(mock_job, mock_job_detail, "llm_llama3_1_8b", "test-dataset")
        )
        mock_model_queries.get_existing_model = AsyncMock(return_value=mock_model)

        await delete_fine_tuning_job(
            mock_db,
            UUID('12345678-1234-5678-1234-567812345678'),
            "test-job"
        )

        assert mock_job.status == FineTuningJobStatus.DELETED
        assert mock_model.status == FineTunedModelStatus.DELETED
        mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_update_job_progress_success(mock_db, mock_job):
    """Test successful job progress update."""
    progress = {
        "current_step": 100,
        "total_steps": 1000,
        "current_epoch": 1,
        "total_epochs": 3
    }
    mock_job.current_step = 90
    mock_job.total_steps = 1000

    result = await update_job_progress(
        mock_db,
        mock_job,
        progress
    )

    assert result is True
    assert mock_job.current_step == 100
    assert mock_job.total_steps == 1000
    mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_jobs_for_status_update(mock_db, mock_job):
    """Test retrieving jobs for status update."""
    with patch('app.services.fine_tuning.ft_queries') as mock_queries:
        mock_queries.get_non_terminal_jobs = AsyncMock(return_value=[mock_job])

        result = await get_jobs_for_status_update(mock_db)

        assert len(result) == 1
        assert result[0] == mock_job
        mock_queries.get_non_terminal_jobs.assert_awaited_once()