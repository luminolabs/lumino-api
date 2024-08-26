from sqlalchemy import delete
from datetime import datetime
from app.models.blacklisted_token import BlacklistedToken
from app.core.database import AsyncSessionLocal
from app.core.config_manager import config
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def cleanup_expired_tokens():
    """
    Removes expired tokens from the blacklisted token table.
    """
    async with AsyncSessionLocal() as db:
        # Delete tokens that have expired from the blacklisted token table
        delete_query = delete(BlacklistedToken).where(BlacklistedToken.expires_at < datetime.utcnow())
        result = await db.execute(delete_query)
        deleted_count = result.rowcount
        await db.commit()
        logger.info(f"Blacklisted tokens cleanup completed. Removed {deleted_count} expired tokens")