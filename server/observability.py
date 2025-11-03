"""
Observability module: structured logging, metrics, and request tracing
"""
from __future__ import annotations
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Optional Prometheus support
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# ============================================================================
# Structured JSON Logging
# ============================================================================

class StructuredLogger:
    """JSON structured logger for production environments"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format log message as JSON or text"""
        if self.use_json:
            log_entry = {
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "logger": self.logger.name,
                **kwargs
            }
            return json.dumps(log_entry)
        else:
            # Text format with extra fields
            extra = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
            return f"{message} {extra}".strip()
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message("ERROR", message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message("DEBUG", message, **kwargs))


# ============================================================================
# Prometheus Metrics
# ============================================================================

if PROMETHEUS_AVAILABLE:
    # Request metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency',
        ['method', 'endpoint']
    )
    
    # LLM metrics
    llm_requests_total = Counter(
        'llm_requests_total',
        'Total LLM requests',
        ['provider', 'model', 'success']
    )
    
    llm_request_duration_seconds = Histogram(
        'llm_request_duration_seconds',
        'LLM request latency',
        ['provider', 'model']
    )
    
    llm_tokens_total = Counter(
        'llm_tokens_total',
        'Total tokens used',
        ['provider', 'model']
    )
    
    llm_retries_total = Counter(
        'llm_retries_total',
        'Total LLM retry attempts',
        ['provider', 'model']
    )
    
    # Application metrics
    active_requests = Gauge(
        'active_requests',
        'Number of active requests'
    )
    
    fallback_responses_total = Counter(
        'fallback_responses_total',
        'Total fallback responses used',
        ['endpoint']
    )


class MetricsCollector:
    """Collect and export Prometheus metrics"""
    
    def __init__(self):
        self.enabled = PROMETHEUS_AVAILABLE and os.getenv("ENABLE_METRICS", "false").lower() == "true"
    
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        if not self.enabled:
            return
        
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_llm_request(
        self,
        provider: str,
        model: str,
        success: bool,
        duration_ms: int,
        tokens: Optional[int] = None,
        retries: int = 0
    ):
        """Record LLM request metrics"""
        if not self.enabled:
            return
        
        llm_requests_total.labels(
            provider=provider,
            model=model,
            success=str(success)
        ).inc()
        
        llm_request_duration_seconds.labels(
            provider=provider,
            model=model
        ).observe(duration_ms / 1000.0)
        
        if tokens:
            llm_tokens_total.labels(provider=provider, model=model).inc(tokens)
        
        if retries > 0:
            llm_retries_total.labels(provider=provider, model=model).inc(retries)
    
    def record_fallback(self, endpoint: str):
        """Record fallback usage"""
        if not self.enabled:
            return
        
        fallback_responses_total.labels(endpoint=endpoint).inc()
    
    def increment_active_requests(self):
        """Increment active request counter"""
        if self.enabled:
            active_requests.inc()
    
    def decrement_active_requests(self):
        """Decrement active request counter"""
        if self.enabled:
            active_requests.dec()
    
    def export_metrics(self) -> tuple[bytes, str]:
        """Export metrics in Prometheus format"""
        if not self.enabled:
            return b"", "text/plain"
        
        return generate_latest(), CONTENT_TYPE_LATEST


# Global instances
metrics_collector = MetricsCollector()
logger = StructuredLogger(__name__)


# ============================================================================
# Request ID Middleware
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID to all requests for correlation"""
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store in request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response
        response.headers["X-Request-ID"] = request_id
        
        return response


# ============================================================================
# Observability Middleware
# ============================================================================

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Combined observability: logging, metrics, timing"""
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Increment active requests
        metrics_collector.increment_active_requests()
        
        # Get request ID (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )
        
        # Process request
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e)
            )
            # Decrement and re-raise
            metrics_collector.decrement_active_requests()
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = int(duration * 1000)
        
        # Add timing header
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        
        # Record metrics
        endpoint = request.url.path
        metrics_collector.record_http_request(
            method=request.method,
            endpoint=endpoint,
            status=status,
            duration=duration
        )
        
        # Log response
        logger.info(
            "Request completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=status,
            duration_ms=duration_ms
        )
        
        # Decrement active requests
        metrics_collector.decrement_active_requests()
        
        return response


# ============================================================================
# Helper Functions
# ============================================================================

def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    return getattr(request.state, "request_id", "unknown")


@asynccontextmanager
async def trace_operation(operation: str, **attributes):
    """Context manager for tracing operations with logging"""
    start_time = time.time()
    
    logger.debug(
        f"Operation started: {operation}",
        operation=operation,
        **attributes
    )
    
    try:
        yield
        duration_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"Operation completed: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            **attributes
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"Operation failed: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            error=str(e),
            **attributes
        )
        raise


def log_llm_metrics(
    provider: str,
    model: str,
    success: bool,
    duration_ms: int,
    tokens: Optional[int] = None,
    retries: int = 0,
    error: Optional[str] = None,
    request_id: Optional[str] = None
):
    """Log LLM request with metrics"""
    # Record in Prometheus
    metrics_collector.record_llm_request(
        provider=provider,
        model=model,
        success=success,
        duration_ms=duration_ms,
        tokens=tokens,
        retries=retries
    )
    
    # Log
    log_data = {
        "provider": provider,
        "model": model,
        "success": success,
        "duration_ms": duration_ms,
        "tokens": tokens,
        "retries": retries,
    }
    
    if request_id:
        log_data["request_id"] = request_id
    
    if error:
        log_data["error"] = error
        logger.error("LLM request failed", **log_data)
    else:
        logger.info("LLM request completed", **log_data)


def log_fallback_usage(endpoint: str, reason: str, request_id: Optional[str] = None):
    """Log fallback usage"""
    metrics_collector.record_fallback(endpoint)
    
    log_data = {
        "endpoint": endpoint,
        "reason": reason,
    }
    
    if request_id:
        log_data["request_id"] = request_id
    
    logger.warning("Fallback response used", **log_data)
