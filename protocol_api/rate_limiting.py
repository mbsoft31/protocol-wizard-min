"""
Rate limiting and request validation middleware
"""
from __future__ import annotations
import time
from collections import defaultdict
from typing import Dict, Optional
import os

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """
    Simple in-memory rate limiter using token bucket algorithm.
    For production, use Redis-based rate limiting (e.g., slowapi, fastapi-limiter).
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        self.rate = requests_per_minute / 60.0  # requests per second
        self.burst = burst_size
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": self.burst, "last_update": time.time()}
        )
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (IP address)"""
        # Try to get real IP from proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _refill_bucket(self, bucket: Dict[str, float]):
        """Refill tokens based on time elapsed"""
        now = time.time()
        time_passed = now - bucket["last_update"]
        bucket["tokens"] = min(
            self.burst,
            bucket["tokens"] + time_passed * self.rate
        )
        bucket["last_update"] = now
    
    def is_allowed(self, request: Request) -> tuple[bool, Optional[float]]:
        """
        Check if request is allowed.
        Returns (allowed, retry_after_seconds)
        """
        client_id = self._get_client_id(request)
        bucket = self.buckets[client_id]
        
        self._refill_bucket(bucket)
        
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, None
        else:
            # Calculate retry-after time
            retry_after = (1 - bucket["tokens"]) / self.rate
            return False, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, burst_size)
        self.enabled = os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true"
        
        # Exempt paths (health checks, metrics, etc.)
        self.exempt_paths = {"/health", "/health/detailed", "/metrics", "/schema"}
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(request)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(int(retry_after) if retry_after else 60)}
            )
        
        response = await call_next(request)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size"""
    
    def __init__(
        self,
        app,
        max_body_size: int = 1024 * 1024  # 1 MB default
    ):
        super().__init__(app)
        self.max_body_size = int(os.getenv("MAX_REQUEST_SIZE", str(max_body_size)))
        self.enabled = os.getenv("ENABLE_SIZE_LIMITING", "true").lower() == "true"
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")
        
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_body_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size: {self.max_body_size} bytes"
                )
        
        response = await call_next(request)
        return response


# ============================================================================
# Advanced Input Validation
# ============================================================================

def validate_subject_text(text: str, max_length: int = 10000) -> None:
    """Validate subject text input"""
    if not text or not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Subject text cannot be empty"
        )
    
    if len(text) > max_length:
        raise HTTPException(
            status_code=422,
            detail=f"Subject text too long. Maximum {max_length} characters"
        )
    
    # Check for suspicious patterns
    suspicious_patterns = [
        "<?php",  # PHP code injection
        "<script",  # XSS attempts
        "javascript:",
        "data:text/html",
    ]
    
    text_lower = text.lower()
    for pattern in suspicious_patterns:
        if pattern in text_lower:
            raise HTTPException(
                status_code=422,
                detail="Subject text contains potentially malicious content"
            )


def validate_model_string(model: str) -> None:
    """Validate model string format"""
    if not model:
        return  # Optional field
    
    # Expected format: "provider:model_name"
    if ":" not in model:
        raise HTTPException(
            status_code=422,
            detail="Model must be in format 'provider:model_name'"
        )
    
    provider, model_name = model.split(":", 1)
    
    # Validate provider
    valid_providers = {"openai", "gemini", "google"}
    if provider.lower() not in valid_providers:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )
    
    # Basic model name validation
    if not model_name or len(model_name) > 100:
        raise HTTPException(
            status_code=422,
            detail="Invalid model name"
        )


def validate_protocol_queries(protocol: Dict) -> None:
    """Validate protocol before generating queries"""
    # Ensure required fields exist
    required_fields = ["keywords", "screening", "sources"]
    
    for field in required_fields:
        if field not in protocol or not protocol[field]:
            raise HTTPException(
                status_code=422,
                detail=f"Protocol missing required field: {field}"
            )
    
    # Validate keywords
    keywords = protocol.get("keywords", {})
    if not keywords.get("include"):
        raise HTTPException(
            status_code=422,
            detail="Protocol must have at least one inclusion keyword"
        )
    
    # Validate sources
    sources = protocol.get("sources", [])
    valid_sources = {
        "openalex", "crossref", "pubmed", "arxiv",
        "scopus", "web_of_science", "ieee", "acm"
    }
    
    invalid_sources = [s for s in sources if s.lower() not in valid_sources]
    if invalid_sources:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sources: {', '.join(invalid_sources)}. "
                   f"Valid sources: {', '.join(sorted(valid_sources))}"
        )


# ============================================================================
# Configuration Helper
# ============================================================================

def get_rate_limit_config() -> Dict[str, int]:
    """Get rate limiting configuration from environment"""
    return {
        "requests_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        "burst_size": int(os.getenv("RATE_LIMIT_BURST", "10")),
        "max_body_size": int(os.getenv("MAX_REQUEST_SIZE", str(1024 * 1024))),
    }
