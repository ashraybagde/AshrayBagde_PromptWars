"""API routes."""
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request

from app.cache import LRUCache
from app.config import settings
from app.gemini_client import AnalysisError, generate
from app.prompts import REFLECT_TASK, SYSTEM_PROMPT, wrap_user_data
from app.schemas import AnalyzeRequest, AnalyzeResponse, ReflectRequest, ReflectResponse

router = APIRouter()
cache = LRUCache()
_hits: dict[str, deque[float]] = defaultdict(deque)


async def rate_limit(request: Request) -> None:
    """Per-IP in-memory sliding-window limiter for AI endpoints."""
    now, q = time.monotonic(), _hits[request.client.host if request.client else "?"]
    while q and now - q[0] > settings.rate_window_s:
        q.popleft()
    if len(q) >= settings.rate_limit:
        raise HTTPException(429, "Too many requests. Please wait a moment.")
    q.append(now)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "healthy"}


async def _run(schema, user: str, payload: dict):  # noqa: ANN001
    key = cache.key({"s": schema.__name__, **payload})
    if (hit := cache.get(key)) is not None:
        return hit
    try:
        result = await generate(schema, SYSTEM_PROMPT, user)
    except AnalysisError:
        raise HTTPException(502, "We couldn't complete the analysis. Please try again.") from None
    cache.put(key, result)
    return result


@router.post("/api/analyze", response_model=AnalyzeResponse, dependencies=[Depends(rate_limit)])
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Round 1: one Gemini call."""
    data = req.model_dump()
    return await _run(AnalyzeResponse, wrap_user_data(data), data)


@router.post("/api/reflect", response_model=ReflectResponse, dependencies=[Depends(rate_limit)])
async def reflect(req: ReflectRequest) -> ReflectResponse:
    """Round 2: one Gemini call."""
    data = req.model_dump()
    return await _run(ReflectResponse, f"{REFLECT_TASK}\n{wrap_user_data(data)}", data)
