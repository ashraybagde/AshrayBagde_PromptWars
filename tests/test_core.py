import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import routes
from app.main import app
from app.safety import has_verdict
from app.schemas import DIMENSIONS, AnalyzeRequest, AnalyzeResponse

COV = [{"dimension": d, "score": 5, "note": "n"} for d in DIMENSIONS]
OK = {"reasoning_summary": "s", "stated_reasons": ["a"], "hidden_assumptions": [],
      "overlooked_factors": [], "internal_conflicts": [],
      "probing_questions": [f"q{i}?" for i in range(5)], "coverage": COV}


def test_schema_trims_and_rejects():
    assert AnalyzeRequest(decision="  x ").decision == "x"
    with pytest.raises(ValidationError):
        AnalyzeRequest(decision="   ")
    with pytest.raises(ValidationError):
        AnalyzeRequest(decision="x" * 501)


@pytest.mark.parametrize("t", ["You should take it", "I recommend A", "The best choice is B"])
def test_verdicts_detected(t):
    assert has_verdict(t)


def test_neutral_text_passes():
    assert not has_verdict("What would change your mind?")


@pytest.fixture
def client(monkeypatch):
    async def fake(schema, system, user):
        return AnalyzeResponse(**OK)
    monkeypatch.setattr(routes, "generate", fake)
    routes._hits.clear()
    return TestClient(app)


def test_health_and_headers(client):
    r = client.get("/health")
    assert r.json() == {"status": "healthy"}
    assert r.headers["x-frame-options"] == "DENY" and "content-security-policy" in r.headers


def test_analyze_ok_and_validation(client):
    assert client.post("/api/analyze", json={"decision": "d"}).status_code == 200
    assert client.post("/api/analyze", json={"decision": ""}).status_code == 422


def test_rate_limit(client):
    codes = [client.post("/api/analyze", json={"decision": f"d{i}"}).status_code for i in range(12)]
    assert 429 in codes
