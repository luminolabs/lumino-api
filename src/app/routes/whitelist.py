from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user, admin_required
from app.core.config_manager import config
from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.whitelist import (
    WhitelistRequestCreate,
    WhitelistRequestResponse,
    WhitelistRequestUpdate
)
from app.services.whitelist import (
    create_whitelist_request,
    get_whitelist_request,
    update_whitelist_status
)

# Set up API router
router = APIRouter(tags=["Whitelist"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/whitelist", response_model=WhitelistRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_to_be_whitelisted(
        request_data: WhitelistRequestCreate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> WhitelistRequestResponse:
    """Submit a new whitelist request."""
    return await create_whitelist_request(db, current_user.id, request_data)


@router.get("/whitelist", response_model=WhitelistRequestResponse)
async def get_whitelist_request_route(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> WhitelistRequestResponse:
    """Get details of the current user's whitelist request."""
    return await get_whitelist_request(db, current_user.id, current_user.id, current_user.is_admin)


@router.get("/whitelist/admin/{user_id}", response_model=WhitelistRequestResponse)
async def get_whitelist_request_admin(
        user_id: UUID,
        current_user: User = Depends(admin_required),  # Admin check
        db: AsyncSession = Depends(get_db),
) -> WhitelistRequestResponse:
    """Get details of any user's whitelist request (admin only)."""
    return await get_whitelist_request(db, user_id, current_user.id, True)


@router.patch("/whitelist/admin/{user_id}/whitelist-status", response_model=WhitelistRequestResponse)
async def update_whitelist_status_route(
        user_id: UUID,
        update_data: WhitelistRequestUpdate,
        current_user: User = Depends(admin_required),  # Admin check
        db: AsyncSession = Depends(get_db),
) -> WhitelistRequestResponse:
    """Update whitelist status (admin only)."""
    update_request = WhitelistRequestUpdate(is_whitelisted=update_data.is_whitelisted, has_signed_nda=None)
    return await update_whitelist_status(db, user_id, update_request)


@router.patch("/whitelist/admin/{user_id}/nda-status", response_model=WhitelistRequestResponse)
async def update_nda_status_route(
        user_id: UUID,
        update_data: WhitelistRequestUpdate,
        current_user: User = Depends(admin_required),  # Admin check
        db: AsyncSession = Depends(get_db),
) -> WhitelistRequestResponse:
    """Update NDA status (admin only)."""
    update_request = WhitelistRequestUpdate(is_whitelisted=None, has_signed_nda=update_data.has_signed_nda)
    return await update_whitelist_status(db, user_id, update_request)

@router.post("/whitelist/computing-providers/batch", status_code=status.HTTP_202_ACCEPTED)
async def add_computing_providers_batch_route(
        request: WhitelistBatchRequest,
        current_user: User = Depends(admin_required),  # Use appropriate permission check
        db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Add multiple computing providers to the whitelist in a single transaction.
    Admin only endpoint.
    """
    return await add_computing_providers_batch(db, request)


@router.delete("/whitelist/computing-providers/batch", status_code=status.HTTP_202_ACCEPTED)
async def remove_computing_providers_batch_route(
        request: WhitelistBatchRequest,
        current_user: User = Depends(admin_required),  # Use appropriate permission check
        db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Remove multiple computing providers from the whitelist in a single transaction.
    Admin only endpoint.
    """
    return await remove_computing_providers_batch(db, request)