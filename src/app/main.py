from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config_manager import config
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
)
from app.core.database import engine, Base
from app.routes import users, api_keys, datasets, fine_tuning, models, usage
from app.tasks.api_key_cleanup import cleanup_expired_api_keys
from app.tasks.token_cleanup import cleanup_expired_tokens

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # -------
    # Run database migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Add the token cleanup task to the background scheduler
    scheduler.add_job(cleanup_expired_tokens, 'interval', minutes=1)
    # Add the API key cleanup task to the background scheduler
    scheduler.add_job(cleanup_expired_api_keys, 'interval', minutes=1)
    # Start the background scheduler
    scheduler.start()

    yield
    # Shutdown
    # --------
    # Stop the background scheduler
    scheduler.shutdown()


app = FastAPI(title="LLM Fine-tuning API", lifespan=lifespan)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

api_prefix = config.api_v1_prefix

app.include_router(users.router, prefix=api_prefix)
app.include_router(api_keys.router, prefix=api_prefix)
app.include_router(datasets.router, prefix=api_prefix)
app.include_router(fine_tuning.router, prefix=api_prefix)
app.include_router(models.router, prefix=api_prefix)
app.include_router(usage.router, prefix=api_prefix)


@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Fine-tuning API"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=5100, reload=True)
