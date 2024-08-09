from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inference_endpoint import InferenceEndpoint
from app.models.inference_query import InferenceQuery
from app.schemas.inference import InferenceEndpointCreate, InferenceEndpointResponse, PromptRequest, PromptResponse
from app.core.inference import create_inference_endpoint_task, delete_inference_endpoint_task, send_prompt_to_endpoint


async def create_inference_endpoint(db: AsyncSession, user_id: UUID, endpoint: InferenceEndpointCreate) -> InferenceEndpointResponse:
    """Create a new inference endpoint."""
    db_endpoint = InferenceEndpoint(
        user_id=user_id,
        fine_tuned_model_id=endpoint.fine_tuned_model_id,
        machine_type=endpoint.machine_type,
        parameters=endpoint.parameters,
        status="creating"
    )
    db.add(db_endpoint)
    await db.commit()
    await db.refresh(db_endpoint)

    # Start the endpoint creation task asynchronously
    await create_inference_endpoint_task(db_endpoint.id)

    return InferenceEndpointResponse.from_orm(db_endpoint)


async def get_inference_endpoints(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> list[InferenceEndpointResponse]:
    """Get all inference endpoints for a user."""
    result = await db.execute(
        select(InferenceEndpoint)
        .where(InferenceEndpoint.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return [InferenceEndpointResponse.from_orm(endpoint) for endpoint in result.scalars().all()]


async def get_inference_endpoint(db: AsyncSession, endpoint_id: UUID) -> InferenceEndpointResponse | None:
    """Get a specific inference endpoint."""
    endpoint = await db.get(InferenceEndpoint, endpoint_id)
    if endpoint:
        return InferenceEndpointResponse.from_orm(endpoint)
    return None


async def delete_inference_endpoint(db: AsyncSession, endpoint_id: UUID) -> None:
    """Delete an inference endpoint."""
    db_endpoint = await db.get(InferenceEndpoint, endpoint_id)
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")

    db_endpoint.status = "deleting"
    await db.commit()

    # Start the endpoint deletion task asynchronously
    await delete_inference_endpoint_task(endpoint_id)


async def send_prompt(db: AsyncSession, endpoint_id: UUID, prompt: PromptRequest) -> PromptResponse:
    """Send a prompt to the model and record the query."""
    db_endpoint = await db.get(InferenceEndpoint, endpoint_id)
    if not db_endpoint:
        raise ValueError("Inference endpoint not found")

    if db_endpoint.status != "running":
        raise ValueError("Inference endpoint is not in a running state")

    response, input_tokens, output_tokens, response_time = await send_prompt_to_endpoint(db_endpoint, prompt.prompt)

    db_query = InferenceQuery(
        inference_endpoint_id=endpoint_id,
        request=prompt.prompt,
        response=response,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        response_time=response_time
    )
    db.add(db_query)
    await db.commit()
    await db.refresh(db_query)

    return PromptResponse.from_orm(db_query)


async def get_conversation_history(db: AsyncSession, endpoint_id: UUID, skip: int = 0, limit: int = 100) -> list[PromptResponse]:
    """Retrieve conversation history for an endpoint."""
    result = await db.execute(
        select(InferenceQuery)
        .where(InferenceQuery.inference_endpoint_id == endpoint_id)
        .order_by(InferenceQuery.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [PromptResponse.from_orm(query) for query in result.scalars().all()]


async def get_prompt(db: AsyncSession, prompt_id: UUID) -> PromptResponse | None:
    """Get a single prompt by ID."""
    query = await db.get(InferenceQuery, prompt_id)
    if query:
        return PromptResponse.from_orm(query)
    return None
