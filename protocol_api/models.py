from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class Picos(BaseModel):
    """PICOS framework for systematic reviews"""
    population: Optional[List[str]] = Field(
        None, description="Target population or subjects"
    )
    intervention: Optional[List[str]] = Field(
        None, description="Intervention being studied"
    )
    comparison: Optional[List[str]] = Field(
        None, description="Comparison or control"
    )
    outcomes: Optional[List[str]] = Field(
        None, description="Outcomes of interest"
    )
    context: Optional[List[str]] = Field(
        None, description="Study context or setting"
    )


class Keywords(BaseModel):
    """Keyword sets for literature search"""
    include: List[str] = Field(..., min_length=1, description="Required keywords")
    exclude: List[str] = Field(default_factory=list, description="Exclusion keywords")
    synonyms: Optional[Dict[str, List[str]]] = Field(
        None, description="Keyword synonyms for query expansion"
    )

    @field_validator("include", "exclude")
    @classmethod
    def validate_non_empty_strings(cls, v: List[str]) -> List[str]:
        """Ensure no empty strings in keyword lists"""
        return [s.strip() for s in v if s.strip()]


class Screening(BaseModel):
    """Screening criteria for study inclusion/exclusion"""
    inclusion_criteria: List[str] = Field(
        ..., min_length=1, description="Criteria for including studies"
    )
    exclusion_criteria: List[str] = Field(
        default_factory=list, description="Criteria for excluding studies"
    )
    years: Tuple[int, int] = Field(
        ..., description="Year range [start, end] for publication dates"
    )
    languages: List[str] = Field(
        default_factory=lambda: ["en"], description="Accepted language codes"
    )
    doc_types: List[str] = Field(
        default_factory=lambda: ["journal", "conference"],
        description="Accepted document types"
    )

    @field_validator("years")
    @classmethod
    def validate_year_range(cls, v: Tuple[int, int]) -> Tuple[int, int]:
        """Ensure valid year range"""
        start, end = v
        if start > end:
            raise ValueError(f"Start year ({start}) must be <= end year ({end})")
        if start < 1900 or end > 2100:
            raise ValueError("Years must be between 1900 and 2100")
        return v


class Protocol(BaseModel):
    """Complete systematic review protocol"""
    research_questions: List[str] = Field(
        ..., min_length=1, description="Primary research questions"
    )
    picos: Optional[Picos] = Field(
        None, description="PICOS framework structure"
    )
    keywords: Keywords = Field(..., description="Search keywords")
    screening: Screening = Field(..., description="Screening criteria")
    sources: List[str] = Field(
        ..., min_length=1, description="Data sources/databases to search"
    )
    rationales: Optional[Dict[str, str]] = Field(
        None, description="Rationale for protocol decisions"
    )


class BorderlineExample(BaseModel):
    """Example of borderline case for screening"""
    text: str = Field(..., description="Description of the borderline case")
    suggested: Literal["INCLUDE", "EXCLUDE", "MAYBE"] = Field(
        ..., description="Suggested decision"
    )
    why: str = Field(..., description="Reasoning for the suggestion")


class Refinements(BaseModel):
    """Refined screening criteria with examples"""
    inclusion_criteria_refined: List[str] = Field(
        ..., description="Refined inclusion criteria"
    )
    exclusion_criteria_refined: List[str] = Field(
        ..., description="Refined exclusion criteria"
    )
    borderline_examples: List[BorderlineExample] = Field(
        default_factory=list, description="Examples of borderline cases"
    )
    risks_and_ambiguities: List[str] = Field(
        default_factory=list, description="Identified risks and ambiguities"
    )


class Query(BaseModel):
    """Database-specific search query"""
    family: str = Field(..., description="Database family (e.g., 'openalex')")
    provider: str = Field(..., description="Specific provider/endpoint")
    native: Dict[str, Any] = Field(..., description="Native query format")
    budget: Dict[str, Any] = Field(
        default_factory=dict, description="Query budget/limits"
    )
    rationale: str = Field(..., description="Reasoning for query design")


class Health(BaseModel):
    """Basic health check response"""
    status: str = Field(..., description="Service status")


class HealthDetailed(BaseModel):
    """Detailed health check with LLM provider status"""
    status: str = Field(..., description="Service status")
    llm_providers: Dict[str, bool] = Field(
        default_factory=dict, description="Status of each LLM provider"
    )
    default_model: str = Field(..., description="Default model being used")


class DraftRequest(BaseModel):
    """Request to generate protocol draft"""
    subject_text: str = Field(
        ..., min_length=10, description="Subject text describing the review topic"
    )
    model: Optional[str] = Field(
        None, description="LLM model to use (overrides default)"
    )


class DraftResponse(BaseModel):
    """Response with generated protocol draft"""
    protocol: Protocol = Field(..., description="Generated protocol")
    checklist: str = Field(..., description="Human-in-loop checklist")
    from_fallback: bool = Field(
        ..., description="Whether fallback was used instead of LLM"
    )
    validation: Dict[str, Any] = Field(
        ..., description="Schema validation results"
    )


class RefineRequest(BaseModel):
    """Request to refine protocol criteria"""
    protocol: Protocol = Field(..., description="Protocol to refine")
    model: Optional[str] = Field(
        None, description="LLM model to use (overrides default)"
    )


class RefineResponse(BaseModel):
    """Response with refined criteria"""
    refinements: Refinements = Field(..., description="Refined criteria")
    from_fallback: bool = Field(
        ..., description="Whether fallback was used instead of LLM"
    )


class QueriesRequest(BaseModel):
    """Request to generate database queries"""
    protocol: Protocol = Field(..., description="Protocol to generate queries from")
    model: Optional[str] = Field(
        None, description="LLM model to use (overrides default)"
    )


class QueriesResponse(BaseModel):
    """Response with generated queries"""
    queries: List[Query] = Field(
        default_factory=list, description="Generated database queries"
    )
    from_fallback: bool = Field(
        ..., description="Whether fallback was used instead of LLM"
    )


class FreezeRequest(BaseModel):
    """Request to freeze protocol with hash"""
    protocol: Protocol = Field(..., description="Protocol to freeze")
    refinements: Optional[Refinements] = Field(
        None, description="Optional refinements to merge before freezing"
    )


class Manifest(BaseModel):
    """Protocol freeze manifest for audit trail"""
    frozen_at_utc: str = Field(..., description="ISO timestamp of freeze")
    protocol_sha256: str = Field(
        ..., description="SHA-256 hash of canonical protocol JSON"
    )
    source_files: List[str] = Field(
        default_factory=list, description="Source files used"
    )
    notes: Optional[str] = Field(None, description="Additional notes")


class FreezeResponse(BaseModel):
    """Response with frozen protocol and manifest"""
    protocol: Protocol = Field(..., description="Final frozen protocol")
    manifest: Manifest = Field(..., description="Freeze manifest with hash")