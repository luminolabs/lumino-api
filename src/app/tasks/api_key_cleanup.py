from sqlalchemy import update
from datetime import datetime
from app.models.api_key import ApiKey
from app.core.constants import ApiKeyStatus
from app.core.database import AsyncSessionLocal
from app.core.config_manager import config
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

async def cleanup_expired_api_keys():
    """
    Marks expired API keys as EXPIRED in a single database query.
    """
    async with AsyncSessionLocal() as session:
        # Update API keys that have expired to EXPIRED status
        update_query = (
            update(ApiKey)
            .where(
                (ApiKey.expires_at < datetime.utcnow()) &
                (ApiKey.status == ApiKeyStatus.ACTIVE)
            )
            .values(status=ApiKeyStatus.EXPIRED)
        )
        result = await session.execute(update_query)
        updated_count = result.rowcount
        await session.commit()
        logger.info(f"Expiration check completed. Marked {updated_count} API keys as expired")