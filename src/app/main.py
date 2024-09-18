from contextlib import asynccontextmanager

import stripe
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app.core.config_manager import config
from app.core.database import engine, Base
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
)
from app.routes import users, api_keys, datasets, fine_tuning, models, usage, auth0, billing
from app.tasks.api_key_cleanup import cleanup_expired_api_keys
from app.tasks.job_status_updater import update_job_statuses

# Create the background task scheduler instance
background_task_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # -------
    # Initialize Stripe
    stripe.api_key = config.stripe_secret_key
    # Run database migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Add the API key cleanup task to the background scheduler
    background_task_scheduler.add_job(cleanup_expired_api_keys, 'interval', minutes=1)
    # Add the job status updater task to the background scheduler
    if config.run_with_scheduler:
        background_task_scheduler.add_job(update_job_statuses, 'interval', seconds=10)
    # Start the background scheduler
    background_task_scheduler.start()

    yield

    # Shutdown
    # --------
    # Stop the background scheduler
    background_task_scheduler.shutdown()

app = FastAPI(title="LLM Fine-tuning API", lifespan=lifespan)

# Add SessionMiddleware for user authentication
app.add_middleware(SessionMiddleware, secret_key=config.app_secret_key)

# Add exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add routers
api_prefix = config.api_v1_prefix
app.include_router(users.router, prefix=api_prefix)
app.include_router(api_keys.router, prefix=api_prefix)
app.include_router(datasets.router, prefix=api_prefix)
app.include_router(fine_tuning.router, prefix=api_prefix)
app.include_router(models.router, prefix=api_prefix)
app.include_router(usage.router, prefix=api_prefix)
app.include_router(auth0.router, prefix=api_prefix)
app.include_router(billing.router, prefix=api_prefix)

# Set up Jinja2 HTML templates
templates = Jinja2Templates(directory="html")

@app.get("/", response_class=HTMLResponse)
async def web_console(request: Request):
    return templates.TemplateResponse("console.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=5100, reload=True)
