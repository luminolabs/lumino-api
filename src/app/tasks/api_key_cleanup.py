from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.utils import setup_logger
from app.queries import api_keys as api_key_queries

logger = setup_logger(__name__)

async def cleanup_expired_api_keys(db: AsyncSession = Depends(get_db)) -> None:
    """Mark expired API keys as EXPIRED in a single transaction."""
    try:
        # Update expired keys to EXPIRED status
        updated_count = await api_key_queries.mark_expired_keys(db)
        await db.commit()

        logger.info(f"Marked {updated_count} API keys as expired")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to cleanup expired API keys: {str(e)}")
