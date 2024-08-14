from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes import users, api_keys, datasets, fine_tuning, models, inference, usage
from app.models import User, Dataset, FineTuningJob, FineTunedModel, InferenceEndpoint, InferenceQuery, ApiKey, Usage
from app.config_manager import config
from app.database import engine, Base
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(title="LLM Fine-tuning API", lifespan=lifespan)

api_prefix = config.api_v1_prefix

app.include_router(users.router, prefix=api_prefix)
app.include_router(api_keys.router, prefix=api_prefix)
app.include_router(datasets.router, prefix=api_prefix)
app.include_router(fine_tuning.router, prefix=api_prefix)
app.include_router(models.router, prefix=api_prefix)
app.include_router(inference.router, prefix=api_prefix)
app.include_router(usage.router, prefix=api_prefix)


@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Fine-tuning API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
