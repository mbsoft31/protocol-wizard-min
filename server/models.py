from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


class Picos(BaseModel):
    population: Optional[List[str]] = None
    intervention: Optional[List[str]] = None
    comparison: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    context: Optional[List[str]] = None


class Keywords(BaseModel):
    include: List[str]
    exclude: List[str]
    synonyms: Optional[Dict[str, List[str]]] = None


class Screening(BaseModel):
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    years: Tuple[int, int]
    languages: List[str]
    doc_types: List[str]


class Protocol(BaseModel):
    research_questions: List[str]
    picos: Optional[Picos] = None
    keywords: Keywords
    screening: Screening
    sources: List[str]
    rationales: Optional[Dict[str, str]] = None


class BorderlineExample(BaseModel):
    text: str
    suggested: Literal["INCLUDE", "EXCLUDE", "MAYBE"]
    why: str


class Refinements(BaseModel):
    inclusion_criteria_refined: List[str]
    exclusion_criteria_refined: List[str]
    borderline_examples: List[BorderlineExample]
    risks_and_ambiguities: List[str]


class Query(BaseModel):
    family: str
    provider: str
    native: Dict[str, Any]
    budget: Dict[str, Any]
    rationale: str


class Health(BaseModel):
    status: str


class DraftRequest(BaseModel):
    subject_text: str
    model: Optional[str] = None


class DraftResponse(BaseModel):
    protocol: Protocol
    checklist: str
    from_fallback: bool
    validation: Dict[str, Any]


class RefineRequest(BaseModel):
    protocol: Protocol
    model: Optional[str] = None


class RefineResponse(BaseModel):
    refinements: Refinements
    from_fallback: bool


class QueriesRequest(BaseModel):
    protocol: Protocol
    model: Optional[str] = None


class QueriesResponse(BaseModel):
    queries: List[Query]
    from_fallback: bool


class FreezeRequest(BaseModel):
    protocol: Protocol
    refinements: Optional[Refinements] = None


class Manifest(BaseModel):
    frozen_at_utc: str
    protocol_sha256: str
    source_files: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class FreezeResponse(BaseModel):
    protocol: Protocol
    manifest: Manifest

