"""
Test LLM fallback behavior and malformed JSON handling
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from server.llm import call_llm_async, LLMConfig, LLMResponse
from server.utils import deep_sort, canonical_json_string


@pytest.mark.asyncio
async def test_malformed_json_triggers_fallback():
    """Test that malformed LLM JSON produces fallback"""
    # Mock LLM to return malformed JSON
    malformed_responses = [
        "```json\n{invalid json}```",
        "Not JSON at all",
        '{"incomplete": ',
        '```\n{"missing": "closing brace"\n```',
    ]
    
    for malformed in malformed_responses:
        mock_response = LLMResponse(
            content=malformed,
            success=True,
            provider="test",
            model="test",
            latency_ms=100,
        )
        
        with patch('server.llm.call_llm_async', return_value=mock_response):
            # Import after patching to use mocked version
            from server.main import api_draft
            from server.models import DraftRequest
            
            response = await api_draft(DraftRequest(subject_text="test subject"))
            
            # Should use fallback when JSON is malformed
            assert response.from_fallback is True
            assert response.protocol is not None


@pytest.mark.asyncio
async def test_empty_llm_response_triggers_fallback():
    """Test that empty/None LLM responses use fallback"""
    configs = [
        LLMResponse(content=None, success=False, provider="test", model="test", latency_ms=0, error="API error"),
        LLMResponse(content="", success=True, provider="test", model="test", latency_ms=0),
        LLMResponse(content="   ", success=True, provider="test", model="test", latency_ms=0),
    ]
    
    for mock_response in configs:
        with patch('server.llm.call_llm_async', return_value=mock_response):
            from server.main import api_draft
            from server.models import DraftRequest
            
            response = await api_draft(DraftRequest(subject_text="test subject"))
            assert response.from_fallback is True


@pytest.mark.asyncio
async def test_llm_timeout_uses_fallback():
    """Test that LLM timeout triggers fallback"""
    mock_response = LLMResponse(
        content=None,
        success=False,
        provider="gemini",
        model="gemini-1.5-flash",
        latency_ms=60000,
        error="Timeout after 60s",
    )
    
    with patch('server.llm.call_llm_async', return_value=mock_response):
        from server.main import api_draft
        from server.models import DraftRequest
        
        response = await api_draft(DraftRequest(subject_text="test subject"))
        assert response.from_fallback is True


@pytest.mark.asyncio
async def test_retry_exhaustion_uses_fallback():
    """Test that exhausted retries use fallback"""
    # Mock to always fail
    async def mock_call(*args, **kwargs):
        return LLMResponse(
            content=None,
            success=False,
            provider="openai",
            model="gpt-4o",
            latency_ms=1000,
            error="All retries exhausted",
        )
    
    with patch('server.llm.call_llm_async', side_effect=mock_call):
        from server.main import api_refine
        from server.models import RefineRequest, Protocol, Keywords, Screening
        
        protocol = Protocol(
            research_questions=["test"],
            keywords=Keywords(include=["test"], exclude=[]),
            screening=Screening(
                inclusion_criteria=["test"],
                exclusion_criteria=[],
                years=(2020, 2025),
                languages=["en"],
                doc_types=["journal"],
            ),
            sources=["test"],
        )
        
        response = await api_refine(RefineRequest(protocol=protocol))
        assert response.from_fallback is True


def test_deep_sort_canonicalization():
    """Test that deep_sort produces stable, deterministic output"""
    # Test case 1: Nested objects with different key orders
    obj1 = {
        "z": "last",
        "a": "first",
        "nested": {
            "z": 1,
            "a": 2,
            "deeper": {
                "z": "deepest",
                "a": "first deep"
            }
        }
    }
    
    obj2 = {
        "nested": {
            "deeper": {
                "a": "first deep",
                "z": "deepest"
            },
            "a": 2,
            "z": 1
        },
        "a": "first",
        "z": "last"
    }
    
    sorted1 = deep_sort(obj1)
    sorted2 = deep_sort(obj2)
    
    # Should produce identical canonical forms
    assert json.dumps(sorted1, sort_keys=True) == json.dumps(sorted2, sort_keys=True)
    
    # Test case 2: Lists should maintain order
    obj_with_list = {
        "items": [3, 1, 2],
        "nested": {"list": ["c", "a", "b"]}
    }
    
    sorted_list = deep_sort(obj_with_list)
    assert sorted_list["items"] == [3, 1, 2]  # Order preserved
    assert sorted_list["nested"]["list"] == ["c", "a", "b"]  # Order preserved


def test_canonical_json_string_stability():
    """Test that canonical_json_string produces identical hashes"""
    protocol1 = {
        "sources": ["arxiv", "pubmed"],
        "screening": {
            "years": [2020, 2025],
            "languages": ["en", "fr"]
        },
        "keywords": {"include": ["AI", "ML"], "exclude": ["robotics"]}
    }
    
    protocol2 = {
        "keywords": {"exclude": ["robotics"], "include": ["AI", "ML"]},
        "screening": {
            "languages": ["en", "fr"],
            "years": [2020, 2025]
        },
        "sources": ["arxiv", "pubmed"]
    }
    
    canonical1 = canonical_json_string(protocol1)
    canonical2 = canonical_json_string(protocol2)
    
    # Should be byte-for-byte identical
    assert canonical1 == canonical2
    
    # Should be compact (no spaces)
    assert " " not in canonical1
    
    # Should have sorted keys at all levels
    assert canonical1.startswith('{"keywords":')


def test_sha256_stability():
    """Test that SHA-256 hashing is stable across runs"""
    from server.utils import sha256_text
    
    test_string = '{"a":1,"b":{"c":2,"d":3}}'
    
    # Should produce same hash every time
    hash1 = sha256_text(test_string)
    hash2 = sha256_text(test_string)
    hash3 = sha256_text(test_string)
    
    assert hash1 == hash2 == hash3
    assert len(hash1) == 64  # SHA-256 produces 64 hex chars
    assert all(c in '0123456789abcdef' for c in hash1)


@pytest.mark.asyncio
async def test_protocol_freeze_hash_reproducibility():
    """Test that freezing same protocol produces same hash"""
    from server.main import app
    
    protocol_data = {
        "research_questions": ["How does X affect Y?"],
        "keywords": {
            "include": ["machine learning", "AI"],
            "exclude": ["robotics"]
        },
        "screening": {
            "inclusion_criteria": ["Has ML method"],
            "exclusion_criteria": ["Review paper"],
            "years": [2020, 2025],
            "languages": ["en"],
            "doc_types": ["journal"]
        },
        "sources": ["arxiv", "pubmed"]
    }
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Freeze twice
        response1 = await client.post("/freeze", json={"protocol": protocol_data})
        response2 = await client.post("/freeze", json={"protocol": protocol_data})
        
        hash1 = response1.json()["manifest"]["protocol_sha256"]
        hash2 = response2.json()["manifest"]["protocol_sha256"]
        
        # Should produce identical hashes
        assert hash1 == hash2


def test_schema_validation_catches_invalid_years():
    """Test that schema validation catches invalid year ranges"""
    from server.models import Screening
    from pydantic import ValidationError
    
    # Start year > end year should fail
    with pytest.raises(ValidationError) as exc_info:
        Screening(
            inclusion_criteria=["test"],
            exclusion_criteria=[],
            years=(2025, 2020),  # Invalid: start > end
            languages=["en"],
            doc_types=["journal"]
        )
    
    assert "Start year" in str(exc_info.value)


def test_schema_validation_year_bounds():
    """Test year bounds validation"""
    from server.models import Screening
    from pydantic import ValidationError
    
    # Year too early
    with pytest.raises(ValidationError):
        Screening(
            inclusion_criteria=["test"],
            exclusion_criteria=[],
            years=(1800, 2025),  # Invalid: < 1900
            languages=["en"],
            doc_types=["journal"]
        )
    
    # Year too late
    with pytest.raises(ValidationError):
        Screening(
            inclusion_criteria=["test"],
            exclusion_criteria=[],
            years=(2020, 2150),  # Invalid: > 2100
            languages=["en"],
            doc_types=["journal"]
        )


@pytest.mark.asyncio
async def test_schema_endpoint_matches_file():
    """Test that /schema endpoint returns same schema as file"""
    from server.main import app
    from pathlib import Path
    import json
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/schema")
        api_schema = response.json()
        
        # Read schema file
        schema_file = json.loads(Path("schemas/protocol.schema.json").read_text())
        
        # Should be identical
        assert api_schema == schema_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
