from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

# Load environment from .env early (if available)
try:
    from dotenv import load_dotenv, find_dotenv
    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(_dotenv_path, override=False)
except Exception:
    # Optional dependency; if missing, env variables must be set externally
    _dotenv_path = None

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from .llm import (
    call_llm_async,
    check_llm_health,
    FALLBACK_DRAFT,
    FALLBACK_REFINEMENTS,
    LLMConfig,
)
from .models import (
    DraftRequest,
    DraftResponse,
    FreezeRequest,
    FreezeResponse,
    Health,
    HealthDetailed,
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

# Configure logging (level from env)
_log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context replacing deprecated on_event hooks."""
    logger.info("=" * 60)
    logger.info("Protocol Wizard API starting up")
    logger.info(f"Default model: {default_model()}")
    logger.info(f"OpenAI configured: {'OPENAI_API_KEY' in os.environ}")
    logger.info(f"Gemini configured: {'GOOGLE_API_KEY' in os.environ}")
    logger.info(f"Allowed origins: {os.getenv('ALLOWED_ORIGINS', '*')}")
    logger.info("=" * 60)
    try:
        yield
    finally:
        logger.info("Protocol Wizard API shutting down")

app = FastAPI(
    title="Protocol Wizard API",
    version="0.2.0",
    description="AI-powered systematic review protocol generation",
    lifespan=lifespan,
)

# Configure CORS - restrict in production!
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        # Add timing header
        response.headers["X-Process-Time-Ms"] = str(int(process_time))
        
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} time={process_time:.2f}ms"
        )
        
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions gracefully"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
        },
    )


def default_model() -> str:
    """Get default model from environment"""
    return os.getenv("DEFAULT_MODEL", "gemini:gemini-1.5-flash")


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment"""
    return LLMConfig(
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
        timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        base_delay=float(os.getenv("LLM_BASE_DELAY", "1.0")),
        max_delay=float(os.getenv("LLM_MAX_DELAY", "10.0")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
    )


@app.get("/health", response_model=Health)
async def health() -> Health:
    """Basic health check"""
    return Health(status="ok")


@app.get("/health/detailed", response_model=HealthDetailed)
async def health_detailed() -> HealthDetailed:
    """Detailed health check including LLM providers"""
    llm_health = await check_llm_health()
    
    return HealthDetailed(
        status="ok",
        llm_providers=llm_health,
        default_model=default_model(),
    )


@app.get("/schema")
async def get_schema() -> Dict[str, Any]:
    """Get the protocol JSON schema"""
    try:
        schema_text = load_text(Path("schemas/protocol.schema.json"))
        return json.loads(schema_text)
    except FileNotFoundError:
        logger.error("Schema file not found")
        raise HTTPException(status_code=500, detail="Schema file not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid schema JSON: {e}")
        raise HTTPException(status_code=500, detail="Invalid schema format")


@app.post("/draft", response_model=DraftResponse)
async def api_draft(req: DraftRequest) -> DraftResponse:
    """
    Generate initial protocol draft from subject text.
    
    Uses LLM to extract research questions, PICOS, keywords, screening criteria,
    and data sources. Falls back to deterministic response if LLM fails.
    """
    model = req.model or default_model()
    logger.info(f"Drafting protocol with model={model}")
    
    try:
        prompt_tmpl = load_text(Path("prompts/01_extract_protocol.txt"))
    except FileNotFoundError:
        logger.error("Draft prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    # Avoid str.format collisions with JSON braces by using simple replacement
    prompt = prompt_tmpl.replace("{subject_text}", req.subject_text)
    
    # Call LLM with retry logic
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(
            f"LLM call failed, using fallback. Error: {response.error}"
        )
        used_fallback = True
        raw = FALLBACK_DRAFT
    else:
        raw = response.content
        logger.info(
            f"LLM call succeeded: tokens={response.tokens_used}, "
            f"latency={response.latency_ms}ms"
        )
    
    # Parse response
    try:
        obj = json.loads(strip_code_fences(raw))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using fallback: {e}")
        used_fallback = True
        obj = json.loads(FALLBACK_DRAFT)
    
    # Validate against schema
    validation = validate_against_schema(obj)
    if not validation["valid"]:
        logger.warning(f"Protocol validation failed: {validation['errors']}")
    
    # Generate checklist
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
async def api_refine(req: RefineRequest) -> RefineResponse:
    """
    Refine inclusion/exclusion criteria with examples and risk assessment.
    
    Takes an existing protocol and generates refined criteria, borderline examples,
    and identifies potential ambiguities.
    """
    model = req.model or default_model()
    logger.info(f"Refining protocol with model={model}")
    
    try:
        prompt_tmpl = load_text(Path("prompts/02_refine_criteria.txt"))
    except FileNotFoundError:
        logger.error("Refine prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.replace("{protocol_json}", proto_json)
    
    # Call LLM
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(
            f"LLM call failed, using fallback. Error: {response.error}"
        )
        used_fallback = True
        raw = FALLBACK_REFINEMENTS
    else:
        raw = response.content
        logger.info(
            f"LLM call succeeded: tokens={response.tokens_used}, "
            f"latency={response.latency_ms}ms"
        )
    
    # Parse response
    try:
        obj = json.loads(strip_code_fences(raw))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using fallback: {e}")
        used_fallback = True
        obj = json.loads(FALLBACK_REFINEMENTS)
    
    return RefineResponse(
        refinements=obj,
        from_fallback=used_fallback,
    )


@app.post("/queries", response_model=QueriesResponse)
async def api_queries(req: QueriesRequest) -> QueriesResponse:
    """
    Generate database-specific search queries from protocol.
    
    Creates optimized queries for different databases (OpenAlex, PubMed, etc.)
    based on the protocol's keywords and screening criteria.
    """
    model = req.model or default_model()
    logger.info(f"Generating queries with model={model}")
    
    try:
        prompt_tmpl = load_text(Path("prompts/03_queries.txt"))
    except FileNotFoundError:
        logger.error("Queries prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.replace("{protocol_json}", proto_json)
    
    # Call LLM
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(
            f"LLM call failed for queries. Error: {response.error}"
        )
        used_fallback = True
        return QueriesResponse(queries=[], from_fallback=True)
    
    logger.info(
        f"LLM call succeeded: tokens={response.tokens_used}, "
        f"latency={response.latency_ms}ms"
    )
    
    # Parse JSONL response
    objs = normalize_jsonl(response.content)
    
    if not objs:
        logger.warning("No queries generated from LLM response")
        used_fallback = True
    
    return QueriesResponse(queries=objs, from_fallback=used_fallback)


@app.post("/freeze", response_model=FreezeResponse)
async def api_freeze(req: FreezeRequest) -> FreezeResponse:
    """
    Freeze protocol with cryptographic hash for reproducibility.
    
    Optionally merges refinements into the protocol, generates SHA-256 hash,
    and creates a manifest for audit trail.
    """
    logger.info("Freezing protocol")
    
    proto = req.protocol.model_dump()
    
    # Merge refinements if provided
    if req.refinements is not None:
        logger.info("Merging refinements into protocol")
        ref = req.refinements.model_dump()
        screening = proto.get("screening", {})
        
        screening["inclusion_criteria"] = ref.get(
            "inclusion_criteria_refined",
            screening.get("inclusion_criteria", [])
        )
        screening["exclusion_criteria"] = ref.get(
            "exclusion_criteria_refined",
            screening.get("exclusion_criteria", [])
        )
        
        proto["screening"] = screening
    
    # Generate canonical JSON and hash
    payload = canonical_json_string(proto)
    checksum = sha256_text(payload)
    
    logger.info(f"Protocol frozen with checksum={checksum[:16]}...")
    
    manifest = Manifest(
        frozen_at_utc=utc_now_iso(),
        protocol_sha256=checksum,
        source_files=["inline"],
        notes="Freeze before data harvesting; include this hash in PRISMA/methods.",
    )
    
    return FreezeResponse(
        protocol=Protocol.model_validate(proto),
        manifest=manifest,
    )


## (startup/shutdown moved into lifespan handler above)


# Entrypoint helper: uvicorn protocol_api.main:app --reload --port 8000
