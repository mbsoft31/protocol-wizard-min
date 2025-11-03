"""
Protocol Wizard API - Fully integrated with observability and rate limiting
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

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

# Import observability and rate limiting
try:
    from .observability import (
        ObservabilityMiddleware,
        RequestIDMiddleware,
        metrics_collector,
        logger,
        get_request_id,
        log_llm_metrics,
        log_fallback_usage,
    )
    from .rate_limiting import (
        RateLimitMiddleware,
        RequestSizeLimitMiddleware,
        validate_subject_text,
        validate_model_string,
        validate_protocol_queries,
        get_rate_limit_config,
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create FastAPI app
app = FastAPI(
    title="Protocol Wizard API",
    version="0.3.0",
    description="AI-powered systematic review protocol generation with full observability",
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add observability middleware
if OBSERVABILITY_AVAILABLE:
    # Request ID should be first
    app.add_middleware(RequestIDMiddleware)
    
    # Then observability (logging, metrics, timing)
    app.add_middleware(ObservabilityMiddleware)
    
    # Rate limiting
    rate_config = get_rate_limit_config()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=rate_config["requests_per_minute"],
        burst_size=rate_config["burst_size"]
    )
    
    # Request size limiting
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_size=rate_config["max_body_size"]
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions gracefully"""
    request_id = get_request_id(request) if OBSERVABILITY_AVAILABLE else "unknown"
    logger.error(f"Unhandled exception", extra={
        "request_id": request_id,
        "path": request.url.path,
        "error": str(exc)
    }, exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
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


# Metrics endpoint (if Prometheus available)
if OBSERVABILITY_AVAILABLE:
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        metrics_data, content_type = metrics_collector.export_metrics()
        return Response(content=metrics_data, media_type=content_type)


@app.post("/draft", response_model=DraftResponse)
async def api_draft(req: DraftRequest, request: Request) -> DraftResponse:
    """Generate initial protocol draft from subject text"""
    request_id = get_request_id(request) if OBSERVABILITY_AVAILABLE else None
    
    # Validate input
    if OBSERVABILITY_AVAILABLE:
        validate_subject_text(req.subject_text)
        if req.model:
            validate_model_string(req.model)
    
    model = req.model or default_model()
    logger.info(f"Drafting protocol", extra={
        "model": model,
        "request_id": request_id,
        "subject_length": len(req.subject_text)
    })
    
    try:
        prompt_tmpl = load_text(Path("prompts/01_extract_protocol.txt"))
    except FileNotFoundError:
        logger.error("Draft prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    
    prompt = prompt_tmpl.format(subject_text=req.subject_text)
    
    # Call LLM with retry logic
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    # Log LLM metrics
    if OBSERVABILITY_AVAILABLE:
        log_llm_metrics(
            provider=response.provider,
            model=response.model,
            success=response.success,
            duration_ms=response.latency_ms,
            tokens=response.tokens_used,
            error=response.error,
            request_id=request_id
        )
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(f"LLM call failed, using fallback. Error: {response.error}")
        if OBSERVABILITY_AVAILABLE:
            log_fallback_usage("/draft", f"LLM failed: {response.error}", request_id)
        used_fallback = True
        raw = FALLBACK_DRAFT
    else:
        raw = response.content
    
    # Parse response
    try:
        obj = json.loads(strip_code_fences(raw))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using fallback: {e}")
        if OBSERVABILITY_AVAILABLE:
            log_fallback_usage("/draft", f"JSON parse error: {e}", request_id)
        used_fallback = True
        obj = json.loads(FALLBACK_DRAFT)
    
    # Validate against schema
    validation = validate_against_schema(obj)
    if not validation["valid"]:
        logger.warning(f"Protocol validation failed: {validation['errors']}")
    
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
async def api_refine(req: RefineRequest, request: Request) -> RefineResponse:
    """Refine inclusion/exclusion criteria"""
    request_id = get_request_id(request) if OBSERVABILITY_AVAILABLE else None
    
    if req.model and OBSERVABILITY_AVAILABLE:
        validate_model_string(req.model)
    
    model = req.model or default_model()
    logger.info(f"Refining protocol", extra={"model": model, "request_id": request_id})
    
    try:
        prompt_tmpl = load_text(Path("prompts/02_refine_criteria.txt"))
    except FileNotFoundError:
        logger.error("Refine prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.format(protocol_json=proto_json)
    
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    if OBSERVABILITY_AVAILABLE:
        log_llm_metrics(
            provider=response.provider,
            model=response.model,
            success=response.success,
            duration_ms=response.latency_ms,
            tokens=response.tokens_used,
            error=response.error,
            request_id=request_id
        )
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(f"LLM call failed, using fallback. Error: {response.error}")
        if OBSERVABILITY_AVAILABLE:
            log_fallback_usage("/refine", f"LLM failed: {response.error}", request_id)
        used_fallback = True
        raw = FALLBACK_REFINEMENTS
    else:
        raw = response.content
    
    try:
        obj = json.loads(strip_code_fences(raw))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using fallback: {e}")
        if OBSERVABILITY_AVAILABLE:
            log_fallback_usage("/refine", f"JSON parse error: {e}", request_id)
        used_fallback = True
        obj = json.loads(FALLBACK_REFINEMENTS)
    
    return RefineResponse(
        refinements=obj,
        from_fallback=used_fallback,
    )


@app.post("/queries", response_model=QueriesResponse)
async def api_queries(req: QueriesRequest, request: Request) -> QueriesResponse:
    """Generate database-specific search queries"""
    request_id = get_request_id(request) if OBSERVABILITY_AVAILABLE else None
    
    if req.model and OBSERVABILITY_AVAILABLE:
        validate_model_string(req.model)
    
    # Validate protocol for queries
    if OBSERVABILITY_AVAILABLE:
        validate_protocol_queries(req.protocol.model_dump())
    
    model = req.model or default_model()
    logger.info(f"Generating queries", extra={"model": model, "request_id": request_id})
    
    try:
        prompt_tmpl = load_text(Path("prompts/03_queries.txt"))
    except FileNotFoundError:
        logger.error("Queries prompt template not found")
        raise HTTPException(status_code=500, detail="Prompt template not found")
    
    proto_json = json.dumps(req.protocol.model_dump(), ensure_ascii=False, indent=2)
    prompt = prompt_tmpl.format(protocol_json=proto_json)
    
    config = get_llm_config()
    response = await call_llm_async(prompt, model=model, config=config)
    
    if OBSERVABILITY_AVAILABLE:
        log_llm_metrics(
            provider=response.provider,
            model=response.model,
            success=response.success,
            duration_ms=response.latency_ms,
            tokens=response.tokens_used,
            error=response.error,
            request_id=request_id
        )
    
    used_fallback = False
    if not response.success or not response.content:
        logger.warning(f"LLM call failed for queries. Error: {response.error}")
        if OBSERVABILITY_AVAILABLE:
            log_fallback_usage("/queries", f"LLM failed: {response.error}", request_id)
        used_fallback = True
        return QueriesResponse(queries=[], from_fallback=True)
    
    objs = normalize_jsonl(response.content)
    
    if not objs:
        logger.warning("No queries generated from LLM response")
        used_fallback = True
    
    return QueriesResponse(queries=objs, from_fallback=used_fallback)


@app.post("/freeze", response_model=FreezeResponse)
async def api_freeze(req: FreezeRequest, request: Request) -> FreezeResponse:
    """Freeze protocol with cryptographic hash"""
    request_id = get_request_id(request) if OBSERVABILITY_AVAILABLE else None
    logger.info("Freezing protocol", extra={"request_id": request_id})
    
    proto = req.protocol.model_dump()
    
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
    
    payload = canonical_json_string(proto)
    checksum = sha256_text(payload)
    
    logger.info(f"Protocol frozen", extra={
        "checksum": checksum[:16],
        "request_id": request_id
    })
    
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


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 60)
    logger.info("Protocol Wizard API starting up")
    logger.info(f"Default model: {default_model()}")
    logger.info(f"OpenAI configured: {'OPENAI_API_KEY' in os.environ}")
    logger.info(f"Gemini configured: {'GOOGLE_API_KEY' in os.environ}")
    logger.info(f"Allowed origins: {allowed_origins}")
    logger.info(f"Observability: {OBSERVABILITY_AVAILABLE}")
    if OBSERVABILITY_AVAILABLE:
        rate_config = get_rate_limit_config()
        logger.info(f"Rate limiting: {os.getenv('ENABLE_RATE_LIMITING', 'false')}")
        logger.info(f"  - Requests/min: {rate_config['requests_per_minute']}")
        logger.info(f"Metrics: {os.getenv('ENABLE_METRICS', 'false')}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
    logger.info("Protocol Wizard API shutting down")