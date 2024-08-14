from typing import Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import Pagination
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
    get_single_prompt,
)
from app.core.authentication import get_current_active_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["Inference"])


@router.post("/inference", response_model=InferenceEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_new_inference_endpoint(
        endpoint: InferenceEndpointCreate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> InferenceEndpointResponse:
    """Create a new inference endpoint."""
    try:
        return await create_inference_endpoint(db, current_user.id, endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inference", response_model=Dict[str, Union[List[InferenceEndpointResponse], Pagination]])
async def list_inference_endpoints(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[InferenceEndpointResponse], Pagination]]:
    """List all inference endpoints for the current user."""
    endpoints, pagination = await get_inference_endpoints(db, current_user.id, page, items_per_page)
    return {
        "data": endpoints,
        "pagination": pagination
    }


@router.get("/inference/{endpoint_name}", response_model=InferenceEndpointResponse)
async def get_inference_endpoint_info(
        endpoint_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> InferenceEndpointResponse:
    """Get information about a specific inference endpoint."""
    endpoint = await get_inference_endpoint(db, current_user.id, endpoint_name)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Inference endpoint not found")
    return endpoint


@router.delete("/inference/{endpoint_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference_endpoint_request(
        endpoint_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific inference endpoint."""
    try:
        await delete_inference_endpoint(db, current_user.id, endpoint_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/inference/{endpoint_name}/prompts", response_model=PromptResponse)
async def send_prompt_to_model(
        endpoint_name: str,
        prompt: PromptRequest,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Send a prompt to the model."""
    try:
        return await send_prompt(db, current_user.id, endpoint_name, prompt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/inference/{endpoint_name}/prompts", response_model=list[PromptResponse])
async def retrieve_conversation_history(
        endpoint_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[PromptResponse]:
    """Retrieve conversation history."""
    try:
        return await get_conversation_history(db, current_user.id, endpoint_name, skip, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/inference/{endpoint_name}/prompts/{prompt_id}", response_model=PromptResponse)
async def get_single_prompt_request(
        endpoint_name: str,
        prompt_id: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Get a single prompt by ID."""
    try:
        return await get_single_prompt(db, current_user.id, endpoint_name, prompt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
