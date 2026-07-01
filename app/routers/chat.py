from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agents.sql_graph import SqlGraph
from app.models import ChatStreamRequest

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/stream", response_class=StreamingResponse)
async def chat_stream(body: ChatStreamRequest, request: Request) -> StreamingResponse:
    graph: SqlGraph = request.app.state.sql_graph
    return StreamingResponse(
        graph.stream(body.question, analyze=body.analyze), media_type="text/event-stream"
    )
