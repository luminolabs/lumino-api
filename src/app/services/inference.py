import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inference_endpoint import InferenceEndpoint
from app.models.inference_query import InferenceQuery
from app.schemas.common import Pagination
from app.schemas.inference import (
    InferenceEndpointCreate,
    InferenceEndpointResponse,
    PromptRequest,
    PromptResponse,
)

# NOTE: This is all dummy. We don't have an inference system yet.


async def create_inference_endpoint(db: AsyncSession, user_id: UUID, endpoint: InferenceEndpointCreate) -> InferenceEndpointResponse:
    """Create a new inference endpoint."""
    db_endpoint = InferenceEndpoint(
        user_id=user_id,
        name=endpoint.name,
        fine_tuned_model_id=endpoint.fine_tuned_model_id,
        machine_type=endpoint.machine_type,
        parameters=endpoint.parameters,
        status="creating"
    )
    db.add(db_endpoint)
    await db.commit()
    await db.refresh(db_endpoint)
    return InferenceEndpointResponse.from_orm(db_endpoint)


async def get_inference_endpoints(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[InferenceEndpointResponse], Pagination]:
    """Get all inference endpoints for a user with pagination."""
    total_count = await db.scalar(
        select(func.count()).select_from(InferenceEndpoint).where(InferenceEndpoint.user_id == user_id)
    )

    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id)
        .offset(offset)
        .limit(items_per_page)
    )
    endpoints = [InferenceEndpointResponse.from_orm(endpoint) for endpoint in result.scalars().all()]

    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return endpoints, pagination


async def get_inference_endpoint(db: AsyncSession, user_id: UUID, endpoint_name: str) -> InferenceEndpointResponse | None:
    """Get a specific inference endpoint."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id, InferenceEndpoint.name == endpoint_name)
    )
    endpoint = result.scalar_one_or_none()
    if endpoint:
        return InferenceEndpointResponse.from_orm(endpoint)
    return None


async def delete_inference_endpoint(db: AsyncSession, user_id: UUID, endpoint_name: str) -> None:
    """Delete an inference endpoint."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id, InferenceEndpoint.name == endpoint_name)
    )
    db_endpoint = result.scalar_one_or_none()
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")
    await db.delete(db_endpoint)
    await db.commit()


async def send_prompt(db: AsyncSession, user_id: UUID, endpoint_name: str, prompt: PromptRequest) -> PromptResponse:
    """Send a prompt to the model."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id, InferenceEndpoint.name == endpoint_name)
    )
    db_endpoint = result.scalar_one_or_none()
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")

    db_query = InferenceQuery(
        inference_endpoint_id=db_endpoint.id,
        request=prompt.prompt,
        response="This is a dummy response",
        input_tokens=len(prompt.prompt.split()),
        output_tokens=5,
        response_time=0.1
    )
    db.add(db_query)
    await db.commit()
    await db.refresh(db_query)
    return PromptResponse.from_orm(db_query)


async def get_conversation_history(db: AsyncSession, user_id: UUID, endpoint_name: str, skip: int = 0, limit: int = 100) -> list[PromptResponse]:
    """Retrieve conversation history."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id, InferenceEndpoint.name == endpoint_name)
    )
    db_endpoint = result.scalar_one_or_none()
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")

    result = await db.execute(
        select(InferenceQuery)
        .where(InferenceQuery.inference_endpoint_id == db_endpoint.id)
        .order_by(InferenceQuery.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [PromptResponse.from_orm(query) for query in result.scalars().all()]


async def get_single_prompt(db: AsyncSession, user_id: UUID, endpoint_name: str, prompt_id: str) -> PromptResponse:
    """Get a single prompt by ID."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id, InferenceEndpoint.name == endpoint_name)
    )
    db_endpoint = result.scalar_one_or_none()
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")

    result = await db.execute(
        select(InferenceQuery)
        .where(InferenceQuery.inference_endpoint_id == db_endpoint.id, InferenceQuery.id == prompt_id)
    )
    db_query = result.scalar_one_or_none()
    if not db_query:
        raise ValueError("Prompt not found")
    return PromptResponse.from_orm(db_query)
