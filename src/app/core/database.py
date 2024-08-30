from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.core.config_manager import config

# Create the database engine
engine = create_async_engine(config.database_url, echo=config.sqlalchemy_log_all)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    """
    Async context manager to handle database sessions.
    This function can be used as a FastAPI dependency to get a database session.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Yield the database session to the function that depends on it
            yield db
        finally:
            # Ensure the session is closed after the function finishes
            await db.close()
