from decimal import Decimal
from typing import Dict, Union, List
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends
from fastapi.params import Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.authentication import get_current_active_user, admin_required
from app.core.common import parse_date
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.billing import CreditDeductRequest, CreditDeductResponse, CreditHistoryResponse
from app.schemas.common import Pagination
from app.services.billing import create_stripe_checkout_session, deduct_credits, add_credits_to_user, get_credit_history

# Set up API router
router = APIRouter(tags=["Billing"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/billing/credits-deduct", response_model=CreditDeductResponse)
async def deduct_and_approve_credits(
    request: CreditDeductRequest,
    # This is an admin only action, don't remove the `admin_required` dependency
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user has enough credits for a job and commit them if so (Internal endpoint).
    """
    has_enough_credits = await deduct_credits(request, db)
    return CreditDeductResponse(has_enough_credits=has_enough_credits)


@router.get("/billing/credit-history", response_model=Dict[str, Union[List[CreditHistoryResponse], Pagination]])
async def get_credit_history_route(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        start_date: str = Query(..., description="Start date for the period (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date for the period (YYYY-MM-DD)"),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[CreditHistoryResponse], Pagination]]:
    """
    Get credit history for the current user.
    """
    # Parse dates
    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)
    # Get credit history
    credit_history, pagination = await get_credit_history(db, current_user.id, start_date_obj, end_date_obj, page, items_per_page)
    return {
        "data": credit_history,
        "pagination": pagination
    }


@router.get("/billing/credits-add")
async def stripe_redirect(
        amount_dollars: int = Query(..., description="The amount of credits to add, in dollars"),
        current_user: User = Depends(get_current_active_user)
):
    """
    Redirect to Stripe for adding credits.
    """
    checkout_session = await create_stripe_checkout_session(
        current_user.id, amount_dollars,
        config.ui_url + config.ui_url_settings + "?stripe_success=1",
        config.ui_url + config.ui_url_settings + "?stripe_error=user_cancelled")
    return RedirectResponse(url=checkout_session.url, status_code=302)


@router.post("/billing/stripe-success-callback")
async def stripe_success_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook callbacks.
    """
    # Get the payload and signature
    payload = await request.body()
    sig_header = request.headers['stripe-signature']

    # Verify the signature and extract the event
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe_webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = UUID(session["client_reference_id"])
        amount_dollars = session["amount_total"] / 100  # Convert cents to dollars
        # Add credits to user's account
        await add_credits_to_user(db, user_id, amount_dollars)
        logger.info(f"Added {amount_dollars} credits to user {user_id}")

    # Return success to Stripe
    return {"status": "success"}