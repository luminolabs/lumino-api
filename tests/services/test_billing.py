from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import stripe

from app.core.constants import BillingTransactionType, UsageUnit, ServiceName, FineTuningJobStatus
from app.core.exceptions import (
    BadRequestError,
    PaymentNeededError,
    ServerError,
    UserNotFoundError
)
from app.models.billing_credit import BillingCredit
from app.models.fine_tuning_job import FineTuningJob
from app.models.user import User
from app.schemas.billing import CreditAddRequest, CreditDeductRequest
from app.services.billing import (
    add_stripe_credits,
    add_manual_credits,
    deduct_credits,
    get_credit_history,
    handle_stripe_webhook,
    calculate_required_credits
)


@pytest.fixture
def mock_user():
    """Create a mock user with necessary attributes."""
    user = MagicMock(spec=User)
    user.id = UUID('12345678-1234-5678-1234-567812345678')
    user.email = "test@example.com"
    user.credits_balance = 100.0
    user.stripe_customer_id = "cus_123"
    return user


@pytest.fixture
def mock_job():
    """Create a mock fine-tuning job."""
    job = MagicMock(spec=FineTuningJob)
    job.id = UUID('98765432-9876-5432-9876-987654321098')
    job.status = FineTuningJobStatus.NEW
    job.provider = MagicMock(value='GCP')
    return job


@pytest.fixture
def credit_deduct_request():
    """Create a sample credit deduct request."""
    return CreditDeductRequest(
        user_id=UUID('12345678-1234-5678-1234-567812345678'),
        usage_amount=1000000,
        usage_unit=UsageUnit.TOKEN,
        service_name=ServiceName.FINE_TUNING_JOB,
        fine_tuning_job_id=UUID('98765432-9876-5432-9876-987654321098')
    )


@pytest.fixture
def credit_add_request():
    """Create a sample credit add request."""
    return CreditAddRequest(
        user_id=UUID('12345678-1234-5678-1234-567812345678'),
        amount=50.0,
        transaction_id="test-transaction"
    )


@pytest.mark.asyncio
async def test_add_stripe_credits_success(mock_user):
    """Test successful Stripe credits addition."""
    mock_session = MagicMock()
    mock_session.url = "https://stripe.com/checkout"

    with patch('app.services.billing.create_stripe_checkout_session',
               return_value=mock_session):
        url = await add_stripe_credits(mock_user, 100, "http://base-url")
        assert url == "https://stripe.com/checkout"


@pytest.mark.asyncio
async def test_add_stripe_credits_error(mock_user):
    """Test error handling in Stripe credits addition."""
    with patch('app.services.billing.create_stripe_checkout_session',
               side_effect=stripe.error.StripeError("Stripe error")):
        with pytest.raises(ServerError) as exc_info:
            await add_stripe_credits(mock_user, 100, "http://base-url")
        assert "Failed to create Stripe checkout session" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_manual_credits_success(mock_db, mock_user, credit_add_request):
    """Test successful manual credits addition."""
    with patch('app.services.billing.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=mock_user)

        result = await add_manual_credits(mock_db, credit_add_request)

        assert result.credits == credit_add_request.amount
        assert result.transaction_type == BillingTransactionType.MANUAL_ADJUSTMENT
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_manual_credits_user_not_found(mock_db, credit_add_request):
    """Test manual credits addition with non-existent user."""
    with patch('app.services.billing.user_queries') as mock_queries:
        mock_queries.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError):
            await add_manual_credits(mock_db, credit_add_request)


@pytest.mark.asyncio
async def test_deduct_credits_success(mock_db, mock_user, mock_job, credit_deduct_request):
    """Test successful credits deduction."""
    with patch('app.services.billing.billing_queries') as mock_billing_queries, \
            patch('app.services.billing.user_queries') as mock_user_queries:
        mock_user_queries.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_billing_queries.get_credit_record = AsyncMock(return_value=None)
        mock_billing_queries.get_job_for_credits = AsyncMock(
            return_value=(mock_job, "llm_llama3_1_8b")
        )

        result = await deduct_credits(credit_deduct_request, mock_db)

        assert result.credits < 0  # Should be negative for deduction
        assert result.transaction_type == BillingTransactionType.FINE_TUNING_JOB
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deduct_credits_insufficient_balance(mock_db, mock_user, mock_job, credit_deduct_request):
    """Test credits deduction with insufficient balance."""
    mock_user.credits_balance = 0.0

    with patch('app.services.billing.billing_queries') as mock_billing_queries, \
            patch('app.services.billing.user_queries') as mock_user_queries, \
            patch('app.services.billing.stripe_charge_offline', return_value=None):
        mock_user_queries.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_billing_queries.get_credit_record = AsyncMock(return_value=None)
        mock_billing_queries.get_job_for_credits = AsyncMock(
            return_value=(mock_job, "llm_llama3_1_8b")
        )

        with pytest.raises(PaymentNeededError):
            await deduct_credits(credit_deduct_request, mock_db)


@pytest.mark.asyncio
async def test_get_credit_history_success(mock_db, mock_user):
    """Test successful credit history retrieval."""
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    with patch('app.services.billing.billing_queries') as mock_queries:
        mock_queries.count_credit_history = AsyncMock(return_value=1)
        mock_queries.get_credit_history = AsyncMock(return_value=[
            BillingCredit(
                id=uuid4(),
                created_at="2024-01-15",
                user_id=mock_user.id,
                credits=50.0,
                transaction_id="test-transaction",
                transaction_type=BillingTransactionType.MANUAL_ADJUSTMENT,
            )
        ])

        result, pagination = await get_credit_history(
            mock_db, mock_user.id, start_date, end_date
        )

        assert len(result) == 1
        assert pagination.total_pages == 1
        assert pagination.current_page == 1


@pytest.mark.asyncio
async def test_get_credit_history_invalid_dates(mock_db, mock_user):
    """Test credit history retrieval with invalid dates."""
    with pytest.raises(BadRequestError):
        await get_credit_history(
            mock_db, mock_user.id, "invalid-date", "2024-01-31"
        )

    with pytest.raises(BadRequestError):
        await get_credit_history(
            mock_db, mock_user.id, "2024-01-31", "2024-01-01"
        )


@pytest.mark.asyncio
async def test_handle_stripe_webhook_charge_success(mock_db, mock_user):
    """Test successful Stripe webhook handling for charge success."""
    charge_data = {
        "type": "charge.succeeded",
        "data": {
            "object": {
                "customer": "cus_123",
                "amount_captured": 10000,  # $100.00
                "id": "ch_123"
            }
        }
    }

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=b"webhook-payload")
    mock_request.headers = {"stripe-signature": "test-signature"}

    with patch('stripe.Webhook.construct_event', return_value=charge_data), \
            patch('app.services.billing.user_queries') as mock_queries:
        mock_queries.get_user_by_stripe_customer_id = AsyncMock(return_value=mock_user)

        result = await handle_stripe_webhook(mock_request, mock_db)
        assert result["status"] == "success"
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_stripe_webhook_customer_update(mock_db, mock_user):
    """Test successful Stripe webhook handling for customer update."""
    customer_data = {
        "type": "customer.updated",
        "data": {
            "object": {
                "id": "cus_123",
                "invoice_settings": {
                    "default_payment_method": "pm_123"
                }
            }
        }
    }

    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=b"webhook-payload")
    mock_request.headers = {"stripe-signature": "test-signature"}

    with patch('stripe.Webhook.construct_event', return_value=customer_data), \
            patch('app.services.billing.user_queries') as mock_queries:
        mock_queries.get_user_by_stripe_customer_id = AsyncMock(return_value=mock_user)

        result = await handle_stripe_webhook(mock_request, mock_db)
        assert result["status"] == "success"
        assert mock_user.stripe_payment_method_id == "pm_123"
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_stripe_webhook_invalid_signature(mock_db):
    """Test Stripe webhook handling with invalid signature."""
    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=b"webhook-payload")
    mock_request.headers = {"stripe-signature": "invalid-signature"}

    with patch('stripe.Webhook.construct_event',
               side_effect=stripe.error.SignatureVerificationError("Invalid", "sig")):
        result = await handle_stripe_webhook(mock_request, mock_db)
        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_calculate_required_credits():
    """Test credit calculation for different scenarios."""
    # Test valid calculation for LLAMA 8B
    result = await calculate_required_credits(
        1000000,  # 1M tokens
        UsageUnit.TOKEN,
        "llm_llama3_1_8b"
    )
    assert result == 2.0  # $2 per million tokens

    # Test valid calculation for LLAMA 70B
    result = await calculate_required_credits(
        1000000,  # 1M tokens
        UsageUnit.TOKEN,
        "llm_llama3_1_70b"
    )
    assert result == 10.0  # $10 per million tokens

    # Test invalid usage unit
    with pytest.raises(BadRequestError):
        await calculate_required_credits(
            1000000,
            "INVALID_UNIT",
            "llm_llama3_1_8b"
        )

    # Test invalid model
    with pytest.raises(BadRequestError):
        await calculate_required_credits(
            1000000,
            UsageUnit.TOKEN,
            "invalid_model"
        )
