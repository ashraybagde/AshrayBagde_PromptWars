"""Gemini integration: structured JSON, timeout, one retry, no-verdict filtering."""
import asyncio
import json
import logging
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.safety import find_violations, sanitize

log = logging.getLogger("blindspot")
T = TypeVar("T", bound=BaseModel)


class AnalysisError(Exception):
    """Raised when Gemini output cannot be used."""


async def _call(system: str, user: str, schema: type[BaseModel]) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    cfg = types.GenerateContentConfig(
        system_instruction=system, response_mime_type="application/json",
        response_schema=schema, temperature=0.4,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    resp = await asyncio.wait_for(
        client.aio.models.generate_content(model=settings.gemini_model, contents=user, config=cfg),
        timeout=settings.timeout_s,
    )
    return resp.text or ""


async def generate(schema: type[T], system: str, user: str) -> T:
    """Call Gemini; retry once on malformed or directive output; sanitize as last resort."""
    last: T | None = None
    for attempt in (1, 2):
        try:
            obj = schema.model_validate_json(await _call(system, user, schema))
        except Exception as exc:  # noqa: BLE001 - any API/parse failure triggers the single retry
            log.warning(json.dumps({"event": "gemini_invalid", "attempt": attempt, "err": type(exc).__name__}))
            continue
        last = obj
        if not find_violations(obj):
            return obj
        log.warning(json.dumps({"event": "verdict_language", "attempt": attempt}))
    if last is None:
        raise AnalysisError("analysis unavailable")
    try:
        return sanitize(last)  # type: ignore[return-value]
    except ValidationError as exc:
        raise AnalysisError("analysis unavailable") from exc
