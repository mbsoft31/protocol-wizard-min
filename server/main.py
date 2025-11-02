from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .llm import call_llm, FALLBACK_DRAFT, FALLBACK_REFINEMENTS
from .models import (
    DraftRequest,
    DraftResponse,
    FreezeRequest,
    FreezeResponse,
    Health,
    Manifest,
    Protocol,
    QueriesRequest,
    QueriesResponse,
    RefineRequest,
    RefineResponse,
)
from .utils import (
    canonical_json_string,
    load_text,
    normalize_jsonl,
    sha256_text,
    strip_code_fences,
    utc_now_iso,
    validate_against_schema,
)

app = FastAPI(title="Protocol Wizard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def default_model() -> str:
    # Default to Gemini to keep OpenAI optional
    return os.getenv("DEFAULT_MODEL", "gemini:gemini-1.5-flash")


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")


@app.get("/schema")
def get_schema() -> Dict[str, Any]:
    return json.loads(load_text(Path("schemas/protocol.schema.json")))


@app.post("/draft", response_model=DraftResponse)
def api_draft(req: DraftRequest) -> DraftResponse:
    model = req.model or default_model()
    prompt_tmpl = load_text(Path("prompts/01_extract_protocol.txt"))
    prompt = prompt_tmpl.format(subject_text=req.subject_text)

    raw = call_llm(prompt, model=model)
    used_fallback = False
    if raw is None:
        used_fallback = True
        raw = FALLBACK_DRAFT

    try:
        obj = json.loads(strip_code_fences(raw))
    except Exception:
        used_fallback = True
        obj = json.loads(FALLBACK_DRAFT)

    validation = validate_against_schema(obj)
    checklist = (
        "# HIL Checklist (Protocol Draft)\n\n"
        "- [ ] Do research questions match the topic?\n"
        "- [ ] Inclusion criteria testable? Any vague words to replace?\n"
        "- [ ] Exclusion criteria complete? Add domain-specific negatives.\n"
        "- [ ] Years/languages/doc types OK?\n"
        "- [ ] Sources sufficient?\n"
        "- [ ] Risks acknowledged?\n\n"
        "Edit outputs/protocol_draft.json and re-run refine.\n"
    )
    return DraftResponse(
        protocol=Protocol.model_validate(obj),
        checklist=checklist,
        from_fallback=used_fallback,
        validation=validation,
    )


@app.post("/refine", response_model=RefineResponse)
def api_refine(req: RefineRequest) -> RefineResponse:
    model = req.model or default_model()
    prompt_tmpl = load_text(Path("prompts/02_refine_criteria.txt"))
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.format(protocol_json=proto_json)

    raw = call_llm(prompt, model=model)
    used_fallback = False
    if raw is None:
        used_fallback = True
        raw = FALLBACK_REFINEMENTS

    try:
        obj = json.loads(strip_code_fences(raw))
    except Exception:
        used_fallback = True
        obj = json.loads(FALLBACK_REFINEMENTS)

    return RefineResponse(
        refinements=obj,  # Pydantic will coerce
        from_fallback=used_fallback,
    )


@app.post("/queries", response_model=QueriesResponse)
def api_queries(req: QueriesRequest) -> QueriesResponse:
    model = req.model or default_model()
    prompt_tmpl = load_text(Path("prompts/03_queries.txt"))
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.format(protocol_json=proto_json)

    raw = call_llm(prompt, model=model)
    used_fallback = False
    if raw is None:
        used_fallback = True
        # No deterministic query fallback — return empty list to mirror FE
        return QueriesResponse(queries=[], from_fallback=True)

    objs = normalize_jsonl(raw)
    # If still empty, treat as fallback
    if not objs:
        used_fallback = True
    return QueriesResponse(queries=objs, from_fallback=used_fallback)


@app.post("/freeze", response_model=FreezeResponse)
def api_freeze(req: FreezeRequest) -> FreezeResponse:
    proto = req.protocol.model_dump()
    if req.refinements is not None:
        ref = req.refinements.model_dump()
        screening = proto.get("screening", {})
        screening["inclusion_criteria"] = ref.get("inclusion_criteria_refined", screening.get("inclusion_criteria", []))
        screening["exclusion_criteria"] = ref.get("exclusion_criteria_refined", screening.get("exclusion_criteria", []))
        proto["screening"] = screening

    payload = canonical_json_string(proto)
    checksum = sha256_text(payload)
    manifest = Manifest(
        frozen_at_utc=utc_now_iso(),
        protocol_sha256=checksum,
        source_files=["inline"],
        notes="Freeze before data harvesting; include this hash in PRISMA/methods.",
    )
    return FreezeResponse(protocol=Protocol.model_validate(proto), manifest=manifest)


# Entrypoint helper: uvicorn server.main:app --reload --port 8000
