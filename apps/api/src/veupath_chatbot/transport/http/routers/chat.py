"""Chat endpoint — starts a background chat operation."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from veupath_chatbot.services.chat.orchestrator import start_chat_stream
from veupath_chatbot.transport.http.deps import (
    CurrentUser,
    StreamRepo,
    UserRepo,
)
from veupath_chatbot.transport.http.schemas import ChatRequest

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", status_code=202)
async def chat(
    request: ChatRequest,
    user_repo: UserRepo,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> JSONResponse:
    """Start a chat operation and return its operation ID.

    The client subscribes to GET /operations/{operationId}/subscribe for SSE events.
    """
    operation_id, strategy_id = await start_chat_stream(
        message=request.message,
        site_id=request.site_id,
        strategy_id=request.strategy_id,
        user_id=user_id,
        user_repo=user_repo,
        stream_repo=stream_repo,
        provider_override=request.provider,
        model_override=request.model_id,
        reasoning_effort=request.reasoning_effort,
        mentions=[m.model_dump(by_alias=True) for m in request.mentions]
        if request.mentions
        else None,
    )
    return JSONResponse(
        {"operationId": operation_id, "strategyId": strategy_id},
        status_code=202,
    )
