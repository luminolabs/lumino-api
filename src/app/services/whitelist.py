from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.exceptions import (
    ForbiddenError,
    BadRequestError,
    NotFoundError
)
from app.core.utils import setup_logger
from app.models.whitelist import Whitelist
from app.queries import whitelist as whitelist_queries
from app.schemas.whitelist import WhitelistRequestCreate, WhitelistRequestUpdate, WhitelistRequestResponse

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_whitelist_request(
        db: AsyncSession,
        user_id: UUID,
        request_data: WhitelistRequestCreate
) -> WhitelistRequestResponse:
    """Create a new whitelist request."""
    # Check if user already has a whitelist request
    existing_request = await whitelist_queries.get_whitelist_by_user_id(db, user_id)
    if existing_request:
        raise BadRequestError(f"User {user_id} already has a whitelist request", logger)

    try:
        # Create whitelist request
        whitelist_request = Whitelist(
            user_id=user_id,
            name=request_data.name,
            email=request_data.email,
            phone_number=request_data.phone_number,
            is_whitelisted=False,
            has_signed_nda=False
        )
        db.add(whitelist_request)
        await db.commit()
        await db.refresh(whitelist_request)

        logger.info(f"Created whitelist request for user: {user_id}")
        return WhitelistRequestResponse.from_orm(whitelist_request)
    except IntegrityError:
        await db.rollback()
        raise BadRequestError(f"User {user_id} already has a whitelist request", logger)
    except Exception as e:
        await db.rollback()
        raise e


async def get_whitelist_request(
        db: AsyncSession,
        user_id: UUID,
        requesting_user_id: UUID,
        is_admin: bool
) -> WhitelistRequestResponse:
    """Get a whitelist request."""
    # Check permissions - only the user themselves or an admin can view the request
    if not is_admin and user_id != requesting_user_id:
        raise ForbiddenError("You don't have permission to view this whitelist request", logger)

    # Get whitelist request
    whitelist_request = await whitelist_queries.get_whitelist_by_user_id(db, user_id)
    if not whitelist_request:
        raise NotFoundError(f"Whitelist request not found for user: {user_id}", logger)

    logger.info(f"Retrieved whitelist request for user: {user_id}")
    return WhitelistRequestResponse.from_orm(whitelist_request)


async def update_whitelist_status(
        db: AsyncSession,
        user_id: UUID,
        update_data: WhitelistRequestUpdate
) -> WhitelistRequestResponse:
    """Update whitelist status - admin only."""
    # Get whitelist request
    whitelist_request = await whitelist_queries.get_whitelist_by_user_id(db, user_id)
    if not whitelist_request:
        raise NotFoundError(f"Whitelist request not found for user: {user_id}", logger)

    try:
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(whitelist_request, field, value)

        await db.commit()
        await db.refresh(whitelist_request)

        logger.info(f"Updated whitelist status for user: {user_id}, data: {update_dict}")
        return WhitelistRequestResponse.from_orm(whitelist_request)
    except Exception as e:
        await db.rollback()
        raise e
    
async def add_computing_providers_batch(
        db: AsyncSession,
        request: WhitelistBatchRequest
) -> Dict[str, Any]:
    """
    Add multiple computing providers to the whitelist.
    Admin/operator only endpoint.

    Args:
        db: Database session
        request: Batch request containing addresses to whitelist

    Returns:
        Dictionary with operation results
        
    Raises:
        ForbiddenError: If the user doesn't have sufficient permissions
    """
    try:
        # Call the contract method
        # This is a placeholder - actual implementation would depend on your web3 setup
        tx_hash = await call_contract_method(
            "addCPBatch",
            [request.addresses]
        )
        
        # Log the operation
        logger.info(f"Added {len(request.addresses)} computing providers to whitelist, tx: {tx_hash}")
        
        return {
            "success": True,
            "message": f"Successfully submitted request to whitelist {len(request.addresses)} computing providers",
            "tx_hash": tx_hash,
            "addresses": request.addresses
        }
    except Exception as e:
        logger.error(f"Failed to add computing providers in batch: {str(e)}")
        raise ServerError(f"Failed to process batch whitelist request: {str(e)}", logger)


async def remove_computing_providers_batch(
        db: AsyncSession,
        request: WhitelistBatchRequest
) -> Dict[str, Any]:
    """
    Remove multiple computing providers from the whitelist.
    Admin/operator only endpoint.

    Args:
        db: Database session
        request: Batch request containing addresses to remove

    Returns:
        Dictionary with operation results
        
    Raises:
        ForbiddenError: If the user doesn't have sufficient permissions
    """
    try:
        # Call the contract method
        # This is a placeholder - actual implementation would depend on your web3 setup
        tx_hash = await call_contract_method(
            "removeCPBatch",
            [request.addresses]
        )
        
        # Log the operation
        logger.info(f"Removed {len(request.addresses)} computing providers from whitelist, tx: {tx_hash}")
        
        return {
            "success": True,
            "message": f"Successfully submitted request to remove {len(request.addresses)} computing providers from whitelist",
            "tx_hash": tx_hash,
            "addresses": request.addresses
        }
    except Exception as e:
        logger.error(f"Failed to remove computing providers in batch: {str(e)}")
        raise ServerError(f"Failed to process batch whitelist removal request: {str(e)}", logger)


# Unsure if this needs to be implemented
async def call_contract_method(method_name: str, args: List) -> str:
    """
    Call a contract method using Web3.
    This is a placeholder - implement according to your Web3 setup.

    Args:
        method_name: Name of the contract method
        args: Arguments to pass to the method

    Returns:
        Transaction hash
    """
    # Implementation depends on your web3 configuration
    # This would typically:
    # 1. Connect to your contract
    # 2. Build the transaction
    # 3. Sign and send the transaction
    # 4. Return the transaction hash
    
    # Placeholder return
    return "0x" + "0" * 64