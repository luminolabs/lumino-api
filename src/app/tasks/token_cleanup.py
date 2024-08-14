from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.blacklisted_token import BlacklistedToken
from app.database import AsyncSessionLocal


async def cleanup_expired_tokens():
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BlacklistedToken).where(BlacklistedToken.expires_at < datetime.utcnow())
        )
        await session.commit()
