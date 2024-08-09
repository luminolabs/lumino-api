from fastapi import FastAPI
from app.routes import users, api_keys, datasets, fine_tuning, models, inference, usage
from app.config_manager import config
from app.database import engine, Base

app = FastAPI(title="LLM Fine-tuning API")

api_prefix = config.api_v1_prefix

app.include_router(users.router, prefix=api_prefix)
app.include_router(api_keys.router, prefix=api_prefix)
app.include_router(datasets.router, prefix=api_prefix)
app.include_router(fine_tuning.router, prefix=api_prefix)
app.include_router(models.router, prefix=api_prefix)
app.include_router(inference.router, prefix=api_prefix)
app.include_router(usage.router, prefix=api_prefix)


@app.on_event("startup")
async def startup():
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Fine-tuning API"}
