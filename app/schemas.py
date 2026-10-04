"""Pydantic v2 request/response models."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DIMENSIONS = [
    "Financial", "Academic/Skills", "Career/Long-term", "Relationships/Family",
    "Health/Wellbeing", "Time/Logistics", "Reversibility/Risk", "Values/Personal Fit",
]


def _text(max_len: int, min_len: int = 0) -> type:
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_len, max_length=max_len)]


class AnalyzeRequest(BaseModel):
    """Guided decision form."""

    model_config = ConfigDict(extra="forbid")
    decision: _text(500, 1)
    options_being_considered: _text(1000) = ""
    main_reasons: _text(1500) = ""
    context_constraints: _text(1500) = ""
    reversibility: _text(300) = ""


class Assumption(BaseModel):
    assumption: str
    why_it_matters: str
    how_to_test: str


class Factor(BaseModel):
    factor: str
    dimension: str
    why_it_matters: str


class Coverage(BaseModel):
    dimension: str
    score: int = Field(ge=0, le=10)
    note: str = ""


class AnalyzeResponse(BaseModel):
    """Round 1 result."""

    reasoning_summary: str
    stated_reasons: list[str]
    hidden_assumptions: list[Assumption]
    overlooked_factors: list[Factor]
    internal_conflicts: list[str]
    probing_questions: list[str] = Field(min_length=5, max_length=7)
    coverage: list[Coverage] = Field(min_length=8, max_length=8)


class ReflectRequest(BaseModel):
    """Round 2 input."""

    model_config = ConfigDict(extra="forbid")
    input: AnalyzeRequest
    analysis: AnalyzeResponse
    answers: list[_text(1000, 1)] = Field(max_length=3)
    assumption_statuses: list[Literal["Verified", "Unsure", "Just a guess"]] = Field(max_length=20)


class ReflectResponse(BaseModel):
    """Round 2 result."""

    what_shifted: str
    newly_surfaced_blind_spots: list[str]
    remaining_open_questions: list[str]
    updated_coverage_scores: list[Coverage] = Field(min_length=8, max_length=8)
