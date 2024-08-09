from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.inference import (
    InferenceEndpointCreate,
    InferenceEndpointResponse,
    PromptRequest,
    PromptResponse,
)
from app.services.inference import (
    create_inference_endpoint,
    get_inference_endpoints,
    get_inference_endpoint,
    delete_inference_endpoint,
    send_prompt,
    get_conversation_history,
    get_prompt,
)
from app.services.user import get_current_user

router = APIRouter(tags=["Inference"])


@router.post("/inference", response_model=InferenceEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_new_inference_endpoint(
        endpoint: InferenceEndpointCreate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> InferenceEndpointResponse:
    """Create a new inference endpoint."""
    try:
        return await create_inference_endpoint(db, current_user["id"], endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inference", response_model=list[InferenceEndpointResponse])
async def list_inference_endpoints(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[InferenceEndpointResponse]:
    """List all inference endpoints."""
    return await get_inference_endpoints(db, current_user["id"], skip, limit)


@router.get("/inference/{endpoint_id}", response_model=InferenceEndpointResponse)
async def get_inference_endpoint_info(
        endpoint_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> InferenceEndpointResponse:
    """Get information about a specific inference endpoint."""
    endpoint = await get_inference_endpoint(db, endpoint_id)
    if not endpoint or endpoint.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    return endpoint


@router.delete("/inference/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference_endpoint_request(
        endpoint_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific inference endpoint."""
    endpoint = await get_inference_endpoint(db, endpoint_id)
    if not endpoint or endpoint.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    try:
        await delete_inference_endpoint(db, endpoint_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inference/{endpoint_id}/prompts", response_model=PromptResponse)
async def send_prompt_to_model(
        endpoint_id: UUID,
        prompt: PromptRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Send a prompt to the model."""
    endpoint = await get_inference_endpoint(db, endpoint_id)
    if not endpoint or endpoint.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    try:
        return await send_prompt(db, endpoint_id, prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inference/{endpoint_id}/prompts", response_model=list[PromptResponse])
async def retrieve_conversation_history(
        endpoint_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[PromptResponse]:
    """Retrieve conversation history."""
    endpoint = await get_inference_endpoint(db, endpoint_id)
    if not endpoint or endpoint.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    return await get_conversation_history(db, endpoint_id, skip, limit)


@router.get("/inference/{endpoint_id}/prompts/{prompt_id}", response_model=PromptResponse)
async def get_single_prompt(
        endpoint_id: UUID,
        prompt_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Get a single prompt by ID."""
    endpoint = await get_inference_endpoint(db, endpoint_id)
    if not endpoint or endpoint.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    prompt = await get_prompt(db, prompt_id)
    if not prompt or prompt.inference_endpoint_id != endpoint_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt
