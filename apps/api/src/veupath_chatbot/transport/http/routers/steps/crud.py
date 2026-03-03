"""GET step endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from veupath_chatbot.transport.http.deps import CurrentUser, StreamRepo
from veupath_chatbot.transport.http.routers.steps._shared import get_step_or_404
from veupath_chatbot.transport.http.schemas import StepResponse

router = APIRouter(prefix="/api/v1/strategies/{strategyId}/steps", tags=["steps"])


@router.get("/{step_id}", response_model=StepResponse)
async def get_step(
    strategyId: UUID,
    step_id: str,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> StepResponse:
    """Get a step from a strategy."""
    _projection, _plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    return StepResponse.model_validate(step)
