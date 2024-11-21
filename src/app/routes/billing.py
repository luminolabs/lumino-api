from typing import Dict, Union, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.authentication import get_current_active_user, admin_required
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.billing import CreditDeductRequest, CreditHistoryResponse, CreditAddRequest
from app.schemas.common import Pagination
from app.services.billing import (
    add_stripe_credits,
    add_manual_credits,
    deduct_credits,
    get_credit_history,
    handle_stripe_webhook, get_stripe_billing_portal_url,
)

router = APIRouter(tags=["Billing"])
logger = setup_logger(__name__)


@router.get("/billing/credit-history", response_model=Dict[str, Union[List[CreditHistoryResponse], Pagination]])
async def get_credit_history_route(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[CreditHistoryResponse], Pagination]]:
    """Get credit history for the current user."""
    credits, pagination = await get_credit_history(
        db, current_user.id, start_date, end_date, page, items_per_page
    )
    return {"data": credits, "pagination": pagination}


@router.get("/billing/stripe-credits-add")
async def stripe_credits_add_route(
        request: Request,
        amount_dollars: int = Query(..., description="Amount to add in dollars"),
        current_user: User = Depends(get_current_active_user),
):
    """Redirect to Stripe for adding credits."""
    checkout_url = await add_stripe_credits(current_user, amount_dollars, str(request.base_url))
    return RedirectResponse(url=checkout_url, status_code=302)


@router.post("/billing/stripe-success-callback")
async def stripe_webhook_handler(
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook callbacks."""
    return await handle_stripe_webhook(request, db)


@router.get("/billing/stripe-payment-method-add")
async def stripe_payment_method_add(
        request: Request,
        current_user: User = Depends(get_current_active_user),
):
    """
    Redirect to Stripe for adding a payment method.
    """
    billing_portal_session_url = await get_stripe_billing_portal_url(current_user, str(request.base_url))
    return RedirectResponse(url=billing_portal_session_url, status_code=302)


# Admin routes
@router.post("/billing/credits-deduct", response_model=CreditHistoryResponse)
async def deduct_credits_route(
        request: CreditDeductRequest,
        _: User = Depends(admin_required),
        db: AsyncSession = Depends(get_db)
):
    """Deduct credits for a job (Internal endpoint)."""
    return await deduct_credits(request, db, retry=True)


@router.post("/billing/credits-add", response_model=CreditHistoryResponse)
async def add_credits_route(
        request: CreditAddRequest,
        _: User = Depends(admin_required),
        db: AsyncSession = Depends(get_db)
):
    """Add credits to a user's account (Admin only)."""
    return await add_manual_credits(db, request)
