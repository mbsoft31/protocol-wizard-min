from __future__ import annotations
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GOOGLE = "google"


@dataclass
class LLMResponse:
    """Structured response from LLM call"""
    content: Optional[str]
    success: bool
    provider: str
    model: str
    latency_ms: int
    tokens_used: Optional[int] = None
    error: Optional[str] = None


@dataclass
class LLMConfig:
    """Configuration for LLM calls"""
    max_retries: int = 3
    timeout_seconds: int = 60
    base_delay: float = 1.0
    max_delay: float = 10.0
    temperature: float = 0.0


async def call_llm_async(
    prompt: str,
    model: str = "gemini:gemini-1.5-flash",
    config: Optional[LLMConfig] = None,
) -> LLMResponse:
    """
    Async call to LLM with retry logic and exponential backoff.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Model identifier in format "provider:model_name"
        config: Configuration for retry/timeout behavior
        
    Returns:
        LLMResponse with content and metadata
    """
    cfg = config or LLMConfig()
    vendor, name = parse_model_string(model)
    
    start_time = time.time()
    last_error = None
    
    for attempt in range(cfg.max_retries):
        try:
            if vendor == LLMProvider.OPENAI:
                response = await _call_openai(prompt, name, cfg)
            elif vendor in (LLMProvider.GEMINI, LLMProvider.GOOGLE):
                response = await _call_gemini(prompt, name, cfg)
            else:
                return LLMResponse(
                    content=None,
                    success=False,
                    provider=vendor.value,
                    model=name,
                    latency_ms=0,
                    error=f"Unsupported provider: {vendor}",
                )
            
            latency_ms = int((time.time() - start_time) * 1000)
            response.latency_ms = latency_ms
            
            if response.success:
                logger.info(
                    f"LLM call succeeded: provider={vendor.value}, model={name}, "
                    f"latency={latency_ms}ms, attempt={attempt+1}"
                )
                return response
            
            last_error = response.error
            
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"LLM call attempt {attempt+1}/{cfg.max_retries} failed: {last_error}"
            )
        
        # Exponential backoff before retry
        if attempt < cfg.max_retries - 1:
            delay = min(cfg.base_delay * (2 ** attempt), cfg.max_delay)
            logger.info(f"Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
    
    # All retries exhausted
    latency_ms = int((time.time() - start_time) * 1000)
    logger.error(
        f"LLM call failed after {cfg.max_retries} attempts: "
        f"provider={vendor.value}, model={name}, error={last_error}"
    )
    
    return LLMResponse(
        content=None,
        success=False,
        provider=vendor.value,
        model=name,
        latency_ms=latency_ms,
        error=last_error,
    )


async def _call_openai(
    prompt: str, model: str, config: LLMConfig
) -> LLMResponse:
    """Call OpenAI API with proper error handling"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return LLMResponse(
            content=None,
            success=False,
            provider="openai",
            model=model,
            latency_ms=0,
            error="OPENAI_API_KEY not set",
        )
    
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=api_key,
            timeout=config.timeout_seconds,
        )
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.temperature,
        )
        
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else None
        
        return LLMResponse(
            content=content,
            success=True,
            provider="openai",
            model=model,
            latency_ms=0,  # Will be set by caller
            tokens_used=tokens,
        )
        
    except Exception as e:
        return LLMResponse(
            content=None,
            success=False,
            provider="openai",
            model=model,
            latency_ms=0,
            error=f"OpenAI API error: {str(e)}",
        )


async def _call_gemini(
    prompt: str, model: str, config: LLMConfig
) -> LLMResponse:
    """Call Google Gemini API with proper error handling"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return LLMResponse(
            content=None,
            success=False,
            provider="gemini",
            model=model,
            latency_ms=0,
            error="GOOGLE_API_KEY not set",
        )
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # Configure generation parameters
        generation_config = {
            "temperature": config.temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        # Run in thread pool since Gemini SDK is synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, model_instance.generate_content, prompt
        )
        
        # Extract text from response
        content = _extract_gemini_text(response)
        
        if not content:
            return LLMResponse(
                content=None,
                success=False,
                provider="gemini",
                model=model,
                latency_ms=0,
                error="No content in Gemini response",
            )
        
        # Try to get token count
        tokens = None
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            tokens = (
                getattr(usage, "prompt_token_count", 0) +
                getattr(usage, "candidates_token_count", 0)
            )
        
        return LLMResponse(
            content=content,
            success=True,
            provider="gemini",
            model=model,
            latency_ms=0,
            tokens_used=tokens,
        )
        
    except Exception as e:
        return LLMResponse(
            content=None,
            success=False,
            provider="gemini",
            model=model,
            latency_ms=0,
            error=f"Gemini API error: {str(e)}",
        )


def _extract_gemini_text(response) -> Optional[str]:
    """Robust text extraction from Gemini response"""
    # Try direct text attribute
    if hasattr(response, "text"):
        try:
            return response.text
        except Exception:
            pass
    
    # Try candidates structure
    try:
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                parts = candidate.content.parts
                return "".join(part.text for part in parts if hasattr(part, "text"))
    except Exception:
        pass
    
    return None


def parse_model_string(model: str) -> tuple[LLMProvider, str]:
    """Parse model string into provider and model name"""
    if ":" in model:
        provider_str, name = model.split(":", 1)
        try:
            provider = LLMProvider(provider_str.lower())
            return provider, name
        except ValueError:
            pass
    
    # Default to OpenAI format for backward compatibility
    return LLMProvider.OPENAI, model


def call_llm(prompt: str, model: str = "gemini:gemini-1.5-flash") -> Optional[str]:
    """
    Synchronous wrapper for backward compatibility.
    
    DEPRECATED: Use call_llm_async instead for better performance.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(call_llm_async(prompt, model))
    return response.content


async def check_llm_health() -> dict[str, bool]:
    """Check health of configured LLM providers"""
    health = {}
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            response = await call_llm_async(
                "test", "openai:gpt-3.5-turbo", LLMConfig(max_retries=1)
            )
            health["openai"] = response.success
        except Exception:
            health["openai"] = False
    
    # Check Gemini
    if os.getenv("GOOGLE_API_KEY"):
        try:
            response = await call_llm_async(
                "test", "gemini:gemini-1.5-flash", LLMConfig(max_retries=1)
            )
            health["gemini"] = response.success
        except Exception:
            health["gemini"] = False
    
    return health


# Fallback responses
FALLBACK_DRAFT = json.dumps({
    "research_questions": [
        "How do deep models generalize from lab to field for plant disease detection?"
    ],
    "picos": {
        "population": ["crop plants"],
        "intervention": ["deep learning detection"],
        "comparison": ["lab vs field"],
        "outcomes": ["accuracy drop"],
        "context": ["field conditions"],
    },
    "keywords": {
        "include": [
            "plant disease detection",
            "domain shift",
            "field images",
            "lab-to-field",
            "generalization",
        ],
        "exclude": ["yield prediction", "irrigation only"],
        "synonyms": {"domain shift": ["dataset shift", "external validity"]},
    },
    "screening": {
        "inclusion_criteria": [
            "disease detection task",
            "machine/deep learning method",
            "includes field images or lab-to-field evaluation",
        ],
        "exclusion_criteria": [
            "yield-only studies",
            "pure irrigation optimization",
            "simulation-only with no field data",
        ],
        "years": [2015, 2025],
        "languages": ["en", "fr", "ar"],
        "doc_types": ["journal", "conference", "preprint"],
    },
    "sources": ["openalex", "crossref", "pubmed", "arxiv"],
    "rationales": {
        "scope": "Focus on robustness and domain shift.",
        "risks": "Non-English coverage might be thin; RS may drift scope.",
    },
})

FALLBACK_REFINEMENTS = json.dumps({
    "inclusion_criteria_refined": [
        "ML vision for plant disease detection",
        "has field images or lab-to-field eval",
    ],
    "exclusion_criteria_refined": [
        "yield-only",
        "irrigation-only",
        "pure simulation",
    ],
    "borderline_examples": [
        {
            "text": "Greenhouse + small field pilot",
            "suggested": "MAYBE",
            "why": "pilot may qualify",
        }
    ],
    "risks_and_ambiguities": ["Remote sensing scope creep"],
})