"""Gemini integration: structured JSON, timeout, one retry, no-verdict filtering."""
import asyncio
import json
import logging
from typing import Any, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.safety import find_violations, sanitize

log = logging.getLogger("blindspot")
T = TypeVar("T", bound=BaseModel)
_RECOVERABLE = (errors.APIError, TimeoutError, ValidationError)


class AnalysisError(Exception):
    """Raised when Gemini output cannot be used."""


def _log(event: str, **fields: Any) -> None:
    log.warning(json.dumps({"severity": "WARNING", "event": event, **fields}))


async def _call(model: str, system: str, user: str, schema: type[BaseModel]) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.4,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    resp = await asyncio.wait_for(
        client.aio.models.generate_content(model=model, contents=user, config=cfg),
        timeout=settings.timeout_s,
    )
    return resp.text or ""


async def generate(schema: type[T], system: str, user: str) -> T:
    """Call Gemini once; on failure or directive output retry once on the fallback model.

    Exactly one call is made on success. After the retry, directive items are stripped.
    """
    last: T | None = None
    models = (settings.gemini_model, settings.gemini_fallback_model)
    for attempt, model in enumerate(models, start=1):
        try:
            obj = schema.model_validate_json(await _call(model, system, user, schema))
        except _RECOVERABLE as exc:
            _log("gemini_failed", attempt=attempt, model=model, err=type(exc).__name__)
            if attempt < len(models):
                await asyncio.sleep(settings.retry_delay_s)
            continue
        last = obj
        if not find_violations(obj):
            return obj
        _log("verdict_language", attempt=attempt, model=model)
    if last is None:
        raise AnalysisError("analysis unavailable")
    try:
        cleaned = sanitize(last)
    except ValidationError as exc:
        raise AnalysisError("analysis unavailable") from exc
    return type(last).model_validate(cleaned.model_dump())
