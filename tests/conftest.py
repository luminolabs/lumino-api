import os

# Set the application environment to `test`
os.environ["CAPI_ENV"] = "test"

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.queries.common import now_utc, make_naive

# Import all models to ensure they are registered with SQLAlchemy [start]
from app.models.api_key import ApiKey
from app.models.base_model import BaseModel
from app.models.billing_credit import BillingCredit
from app.models.dataset import Dataset
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.usage import Usage
from app.models.user import User
# Import all models to ensure they are registered with SQLAlchemy [end]


@pytest.fixture
def mock_db():
    """Create a mock database session that modifies objects."""
    db = AsyncMock(spec=AsyncSession)

    # Make db.refresh() actually modify the object
    async def mock_refresh(obj):
        # Simulate auto-generated fields
        if not getattr(obj, 'id', None):
            obj.id = uuid4()
        if not getattr(obj, 'created_at', None):
            obj.created_at = make_naive(now_utc())
        if not getattr(obj, 'updated_at', None):
            obj.updated_at = make_naive(now_utc())

    # Set the side effect of the mock
    db.refresh.side_effect = mock_refresh

    return db
