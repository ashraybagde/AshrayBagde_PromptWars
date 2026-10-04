import json

import pytest

from app import gemini_client as gc
from app.safety import sanitize
from app.schemas import DIMENSIONS, AnalyzeResponse

COV = [{"dimension": d, "score": 5, "note": "n"} for d in DIMENSIONS]


def payload(question="What matters most?"):
    return json.dumps({"reasoning_summary": "s", "stated_reasons": ["a"], "hidden_assumptions": [],
                       "overlooked_factors": [], "internal_conflicts": [],
                       "probing_questions": [question] * 5, "coverage": COV})


def script(monkeypatch, outputs):
    calls = []

    async def no_sleep(_: float) -> None:
        return None

    async def fake(model, system, user, schema):
        calls.append(model)
        out = outputs[min(len(calls) - 1, len(outputs) - 1)]
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(gc, "_call", fake)
    monkeypatch.setattr(gc.asyncio, "sleep", no_sleep)
    return calls


async def test_valid_json_single_call(monkeypatch):
    calls = script(monkeypatch, [payload()])
    assert (await gc.generate(AnalyzeResponse, "s", "u")).reasoning_summary == "s"
    assert len(calls) == 1


async def test_malformed_then_retry_succeeds(monkeypatch):
    calls = script(monkeypatch, ["not json", payload()])
    assert await gc.generate(AnalyzeResponse, "s", "u")
    assert len(calls) == 2


async def test_final_failure_raises(monkeypatch):
    calls = script(monkeypatch, ["bad", TimeoutError()])
    with pytest.raises(gc.AnalysisError):
        await gc.generate(AnalyzeResponse, "s", "u")
    assert len(calls) == 2


async def test_verdict_retried_then_sanitized(monkeypatch):
    calls = script(monkeypatch, [payload("You should accept it?")])
    with pytest.raises(gc.AnalysisError):  # sanitizing drops all 5 questions -> schema invalid
        await gc.generate(AnalyzeResponse, "s", "u")
    assert len(calls) == 2


def test_sanitize_drops_directive_items():
    obj = AnalyzeResponse.model_validate_json(payload())
    obj.internal_conflicts = ["Fine tension", "I recommend option A"]
    assert sanitize(obj).internal_conflicts == ["Fine tension"]


async def test_retry_uses_fallback_model(monkeypatch):
    calls = script(monkeypatch, [TimeoutError(), payload()])
    await gc.generate(AnalyzeResponse, "s", "u")
    assert calls == [gc.settings.gemini_model, gc.settings.gemini_fallback_model]
