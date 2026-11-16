from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class Ask(BaseModel):
    question: str = Field(min_length=8, max_length=1200)
    as_of: date = Field(default_factory=date.today)


class Search(BaseModel):
    query: str = Field(min_length=3, max_length=240)
    source_type: Literal["all", "regulatory", "label", "research"] = "all"


class Plan(BaseModel):
    in_scope: bool
    reason: str = Field(max_length=600)
    searches: list[Search] = Field(default_factory=list, max_length=3)


class Citation(BaseModel):
    passage_id: str
    quote: str = Field(min_length=3, max_length=350)


class Claim(BaseModel):
    text: str = Field(min_length=5, max_length=550)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class Draft(BaseModel):
    claims: list[Claim] = Field(default_factory=list, max_length=6)
    limitations: list[str] = Field(default_factory=list, max_length=4)


class Judgment(BaseModel):
    claim_index: int
    verdict: Literal["supported", "partial", "unsupported"]
    reason: str = Field(max_length=500)


class Verification(BaseModel):
    judgments: list[Judgment]

