from unittest.mock import MagicMock, patch

import pytest
import stripe

from app.core.exceptions import ServerError
from app.core.stripe_client import (
    create_stripe_customer,
    create_stripe_checkout_session,
    create_stripe_billing_portal_session,
    stripe_charge_offline
)


@pytest.fixture
def mock_user():
    """Create a mock user with necessary attributes."""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.name = "Test User"
    user.stripe_customer_id = None
    return user

@pytest.mark.asyncio
async def test_create_stripe_customer_new(mock_db, mock_user):
    """Test creating a new Stripe customer."""
    # Mock Stripe customer creation
    mock_stripe_customer = MagicMock()
    mock_stripe_customer.id = "cus_123"

    with patch('stripe.Customer.list', return_value=None), \
            patch('stripe.Customer.create', return_value=mock_stripe_customer):

        # Call function
        result = await create_stripe_customer(mock_db, mock_user)

        # Verify Stripe API calls
        stripe.Customer.list.assert_called_once_with(email=mock_user.email)
        stripe.Customer.create.assert_called_once_with(
            email=mock_user.email,
            name=mock_user.name
        )

        # Verify database updates
        assert mock_user.stripe_customer_id == "cus_123"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_user)
        assert result == mock_stripe_customer

@pytest.mark.asyncio
async def test_create_stripe_customer_existing(mock_db, mock_user):
    """Test handling existing Stripe customer."""
    # Mock existing Stripe customer
    mock_stripe_customer = MagicMock()
    mock_stripe_customer.id = "cus_existing"
    mock_customer_list = MagicMock(data=[mock_stripe_customer])

    with patch('stripe.Customer.list', return_value=mock_customer_list), \
            patch('stripe.Customer.create') as mock_create:

        # Call function
        result = await create_stripe_customer(mock_db, mock_user)

        # Verify Stripe API calls
        stripe.Customer.list.assert_called_once_with(email=mock_user.email)
        mock_create.assert_not_called()

        # Verify database updates
        assert mock_user.stripe_customer_id == "cus_existing"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_user)
        assert result == mock_stripe_customer

@pytest.mark.asyncio
async def test_create_stripe_customer_with_id(mock_db, mock_user):
    """Test when user already has a Stripe customer ID."""
    mock_user.stripe_customer_id = "cus_existing"
    mock_stripe_customer = MagicMock()

    with patch('stripe.Customer.retrieve', return_value=mock_stripe_customer) as mock_retrieve, \
            patch('stripe.Customer.list') as mock_list, \
            patch('stripe.Customer.create') as mock_create:

        result = await create_stripe_customer(mock_db, mock_user)

        # Verify only retrieve was called
        mock_retrieve.assert_called_once_with("cus_existing")
        mock_list.assert_not_called()
        mock_create.assert_not_called()
        assert result == mock_stripe_customer

@pytest.mark.asyncio
async def test_create_stripe_customer_error(mock_db, mock_user):
    """Test handling Stripe API errors."""
    with patch('stripe.Customer.list', side_effect=stripe.error.StripeError("Test error")):
        result = await create_stripe_customer(mock_db, mock_user)
        assert result is None
        mock_db.commit.assert_not_awaited()

def test_create_stripe_checkout_session():
    """Test creating a Stripe checkout session."""
    mock_user = MagicMock()
    mock_user.stripe_customer_id = "cus_123"
    mock_session = MagicMock()

    with patch('stripe.checkout.Session.create', return_value=mock_session):
        result = create_stripe_checkout_session(
            mock_user,
            amount_dollars=100,
            success_url="http://success",
            cancel_url="http://cancel"
        )

        # Verify Stripe API call
        stripe.checkout.Session.create.assert_called_once_with(
            payment_method_types=['card'],
            customer=mock_user.stripe_customer_id,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Lumino Credits',
                    },
                    'unit_amount': 10000,  # $100 in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="http://success",
            cancel_url="http://cancel",
            client_reference_id=mock_user.id,
        )
        assert result == mock_session

def test_create_stripe_checkout_session_error():
    """Test handling errors in checkout session creation."""
    mock_user = MagicMock()
    mock_user.stripe_customer_id = "cus_123"

    with patch('stripe.checkout.Session.create',
               side_effect=stripe.error.StripeError("Test error")), \
            pytest.raises(ServerError) as exc_info:
        create_stripe_checkout_session(
            mock_user,
            amount_dollars=100,
            success_url="http://success",
            cancel_url="http://cancel"
        )
    assert "Error creating Stripe checkout session" in str(exc_info.value)

def test_create_stripe_billing_portal_session():
    """Test creating a Stripe billing portal session."""
    mock_user = MagicMock()
    mock_user.stripe_customer_id = "cus_123"
    mock_session = MagicMock()

    with patch('stripe.billing_portal.Session.create', return_value=mock_session):
        result = create_stripe_billing_portal_session(
            mock_user,
            success_url="http://success"
        )

        # Verify Stripe API call
        stripe.billing_portal.Session.create.assert_called_once_with(
            customer=mock_user.stripe_customer_id,
            return_url="http://success"
        )
        assert result == mock_session

def test_stripe_charge_offline_success():
    """Test successful offline Stripe charge."""
    mock_user = MagicMock()
    mock_user.stripe_customer_id = "cus_123"
    mock_invoice = MagicMock()

    with patch('stripe.Invoice.create', return_value=mock_invoice), \
            patch('stripe.InvoiceItem.create') as mock_item_create, \
            patch('stripe.Invoice.finalize_invoice') as mock_finalize, \
            patch('stripe.Invoice.pay') as mock_pay:

        result = stripe_charge_offline(mock_user, 100.50)

        # Verify Stripe API calls
        stripe.Invoice.create.assert_called_once_with(
            customer=mock_user.stripe_customer_id,
            auto_advance=True
        )
        mock_item_create.assert_called_once_with(
            customer=mock_user.stripe_customer_id,
            amount=10050,  # $100.50 in cents
            currency='usd',
            description='Lumino Credits (auto-charge)',
            invoice=mock_invoice.id
        )
        mock_finalize.assert_called_once_with(mock_invoice.id)
        mock_pay.assert_called_once_with(mock_invoice.id)
        assert result == mock_invoice

def test_stripe_charge_offline_error():
    """Test handling errors in offline charging."""
    mock_user = MagicMock()
    mock_user.stripe_customer_id = "cus_123"

    with patch('stripe.Invoice.create', side_effect=stripe.error.StripeError("Test error")):
        result = stripe_charge_offline(mock_user, 100.50)
        assert result is None