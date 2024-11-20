from math import ceil

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.exceptions import ServerError
from app.core.utils import setup_logger
from app.models.user import User

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_stripe_customer(db: AsyncSession, user: User) -> stripe.Customer | None:
    """
    Creates a new customer in Stripe.
    """
    try:
        stripe_customer = None

        # Check if the user already has a Stripe customer ID
        if user.stripe_customer_id:
            return stripe.Customer.retrieve(user.stripe_customer_id)

        # Search if the customer already exists in Stripe
        stripe_customers = stripe.Customer.list(email=user.email)
        if stripe_customers:
            stripe_customer = stripe_customers.data[0]

        # Create the customer in Stripe
        if not stripe_customer:
            stripe_customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
            )

        # Update the user with the Stripe customer ID
        user.stripe_customer_id = stripe_customer.id
        await db.commit()
        await db.refresh(user)  # Refreshes the updated_at field
        return stripe_customer
    except stripe.error.StripeError as e:
        print(f"Stripe error for user: {user.id} message: {e.user_message}")
        return None


def create_stripe_checkout_session(
        user: User,
        amount_dollars: int,
        success_url: str,
        cancel_url: str
) -> stripe.checkout.Session:
    """
    Create a Stripe Checkout Session for adding credits.
    Generates a URL that the user can visit to add credits to their account.
    """
    try:
        # Create the Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer=user.stripe_customer_id,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Lumino Credits',
                    },
                    'unit_amount': ceil(amount_dollars * 100),  # Convert dollars to cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user.id,
        )
        return session
    except Exception as e:
        raise ServerError(f"Error creating Stripe checkout session: {str(e)}", logger)


def create_stripe_billing_portal_session(user: User, success_url: str) -> stripe.billing_portal.Session:
    """
    Create a Customer Portal session.
    Generates a URL that the user can visit to manage their billing information.
    """
    # Create a Customer Portal session
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=success_url
    )
    return session


def stripe_charge_offline(user: User, amount: float) -> stripe.Invoice | None:
    """
    Charges a Stripe customer by creating an invoice and automatically charging their default payment method.
    """
    try:
        # Create the Invoice and Auto-Charge
        invoice = stripe.Invoice.create(
            customer=user.stripe_customer_id,
            auto_advance=True  # Auto-finalize and charge the customer immediately
        )
        # Create Invoice Items for each item in the list
        stripe.InvoiceItem.create(
            customer=user.stripe_customer_id,
            amount=ceil(amount * 100),  # Convert dollars to cents
            currency='usd',
            description='Lumino Credits (auto-charge)',
            invoice=invoice.id
        )
        # Finalize and Charge (if auto_advance is True, this will happen automatically)
        stripe.Invoice.finalize_invoice(invoice.id)
        stripe.Invoice.pay(invoice.id)
        return invoice

    except stripe.error.StripeError as e:
        # Handle Stripe errors
        print(f"Stripe error: {e.user_message}")
        return None
