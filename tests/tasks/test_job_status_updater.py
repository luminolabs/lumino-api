from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.constants import FineTuningJobStatus
from app.tasks.job_status_updater import (
    update_job_statuses,
    _get_jobs_for_update,
    _group_jobs_by_user,
    _update_job_group,
    _process_job_update,
    _update_job_timestamps,
    _update_job_steps,
    _check_create_model
)


@pytest.fixture
def mock_job():
    """Create a mock fine-tuning job."""
    job = MagicMock()
    job.id = UUID('12345678-1234-5678-1234-567812345678')
    job.user_id = UUID('98765432-9876-5432-9876-987654321098')
    job.status = FineTuningJobStatus.RUNNING
    job.current_step = 50
    job.total_steps = 100
    job.current_epoch = 1
    job.total_epochs = 3
    return job


@pytest.fixture
def mock_job_detail():
    """Create a mock job detail."""
    detail = MagicMock()
    detail.timestamps = {}
    detail.parameters = {"batch_size": 2, "epochs": 3}
    return detail


@pytest.mark.asyncio
async def test_update_job_statuses(mock_db, mock_job):
    """Test the main job status update function."""
    with patch('app.tasks.job_status_updater._get_jobs_for_update') as mock_get_jobs, \
            patch('app.tasks.job_status_updater._update_job_group') as mock_update_group:
        # Mock jobs retrieval
        mock_get_jobs.return_value = [mock_job]
        mock_update_group.return_value = None

        await update_job_statuses(mock_db)

        # Verify correct function calls
        mock_get_jobs.assert_awaited_once_with(mock_db)
        mock_update_group.assert_awaited_once_with(
            mock_db,
            mock_job.user_id,
            [mock_job.id]
        )


@pytest.mark.asyncio
async def test_get_jobs_for_update(mock_db):
    """Test retrieving jobs that need updates."""
    with patch('app.tasks.job_status_updater.ft_queries') as mock_queries:
        # Configure mock
        mock_queries.get_jobs_for_status_update = AsyncMock(return_value=[])

        result = await _get_jobs_for_update(mock_db)

        # Verify query was called with correct parameters
        mock_queries.get_jobs_for_status_update.assert_awaited_once()
        assert isinstance(result, list)


def test_group_jobs_by_user(mock_job):
    """Test grouping jobs by user ID."""
    jobs = [mock_job]
    result = _group_jobs_by_user(jobs)

    assert len(result) == 1
    assert mock_job.user_id in result
    assert result[mock_job.user_id] == [mock_job.id]


@pytest.mark.asyncio
async def test_update_job_group_success(mock_db, mock_job):
    """Test successful update of a job group."""
    user_id = UUID('98765432-9876-5432-9876-987654321098')
    job_ids = [UUID('12345678-1234-5678-1234-567812345678')]

    # Mock job updates from scheduler
    job_updates = [{
        'job_id': str(job_ids[0]),
        'status': 'RUNNING',
        'timestamps': {},
        'artifacts': {}
    }]

    with patch('app.tasks.job_status_updater.fetch_job_details') as mock_fetch, \
            patch('app.tasks.job_status_updater._process_job_update') as mock_process:
        mock_fetch.return_value = job_updates
        mock_process.return_value = None

        await _update_job_group(mock_db, user_id, job_ids)

        # Verify interactions
        mock_fetch.assert_awaited_once_with(user_id, job_ids)
        mock_process.assert_awaited_once()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_job_update(mock_db, mock_job, mock_job_detail):
    """Test processing a single job update."""
    update = {
        'job_id': str(mock_job.id),
        'status': 'COMPLETED',
        'timestamps': {'completed': '2024-01-01T00:00:00Z'},
        'artifacts': {
            'job_logger': [{
                'operation': 'step',
                'data': {
                    'step_num': 75,
                    'step_len': 100,
                    'epoch_num': 2,
                    'epoch_len': 3
                }
            }]
        }
    }

    with patch('app.tasks.job_status_updater.ft_queries') as mock_queries, \
            patch('app.tasks.job_status_updater._update_job_timestamps') as mock_update_timestamps, \
            patch('app.tasks.job_status_updater._update_job_steps') as mock_update_steps, \
            patch('app.tasks.job_status_updater._check_create_model') as mock_check_model:
        # Configure mocks
        mock_queries.get_job_by_id = AsyncMock(return_value=mock_job)

        await _process_job_update(mock_db, update, mock_job.user_id)

        # Verify job status was updated
        assert mock_job.status == FineTuningJobStatus.COMPLETED

        # Verify all update functions were called
        mock_update_timestamps.assert_awaited_once()
        mock_update_steps.assert_awaited_once()
        mock_check_model.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_job_timestamps(mock_job, mock_job_detail):
    """Test updating job timestamps."""
    timestamps = {
        'WAIT_FOR_VM': '2024-01-01T00:00:00Z',
        'RUNNING': '2024-01-01T00:01:00Z',
        'COMPLETED': '2024-01-01T00:02:00Z'
    }

    # Mock job details
    mock_job.details = mock_job_detail

    await _update_job_timestamps(mock_job, timestamps)

    # Verify timestamps were correctly mapped and stored
    assert mock_job.details.timestamps.get('running') == timestamps['RUNNING']
    assert mock_job.details.timestamps.get('completed') == timestamps['COMPLETED']
    assert mock_job.details.timestamps.get('queued') == timestamps['WAIT_FOR_VM']


@pytest.mark.asyncio
async def test_update_job_steps(mock_db, mock_job):
    """Test updating job progress steps."""
    artifacts = {
        'job_logger': [{
            'operation': 'step',
            'data': {
                'step_num': 75,
                'step_len': 100,
                'epoch_num': 2,
                'epoch_len': 3
            }
        }]
    }

    # Mock job details
    mock_job.current_step = 50

    await _update_job_steps(mock_db, mock_job, mock_job.user_id, artifacts)

    # Verify job progress was updated
    assert mock_job.current_step == 75
    assert mock_job.total_steps == 100
    assert mock_job.current_epoch == 2
    assert mock_job.total_epochs == 3


@pytest.mark.asyncio
async def test_check_create_model(mock_db, mock_job):
    """Test checking and creating fine-tuned model."""
    artifacts = {
        'job_logger': [{
            'operation': 'weights',
            'data': {
                'weight_files': ['model.pt'],
                'base_url': 'gs://bucket/user/job'
            }
        }]
    }

    with patch('app.tasks.job_status_updater.create_fine_tuned_model') as mock_create:
        mock_create.return_value = True

        await _check_create_model(mock_db, mock_job.id, mock_job.user_id, artifacts)

        # Verify model creation was attempted
        mock_create.assert_awaited_once_with(
            mock_db,
            mock_job.id,
            mock_job.user_id,
            artifacts['job_logger'][0]['data']
        )
