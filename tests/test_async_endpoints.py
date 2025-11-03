"""
Async tests for Protocol Wizard API endpoints
"""
import pytest
from httpx import AsyncClient, ASGITransport
from server.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test basic health endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_detailed_endpoint():
    """Test detailed health endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "llm_providers" in data
        assert "default_model" in data


@pytest.mark.asyncio
async def test_schema_endpoint():
    """Test schema retrieval"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/schema")
        assert response.status_code == 200
        schema = response.json()
        assert "$schema" in schema or "type" in schema


@pytest.mark.asyncio
async def test_draft_endpoint_with_fallback():
    """Test draft endpoint (will use fallback without API keys)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/draft",
            json={
                "subject_text": "Machine learning for plant disease detection in field conditions"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "protocol" in data
        assert "checklist" in data
        assert "from_fallback" in data
        assert "validation" in data
        
        # Check protocol structure
        protocol = data["protocol"]
        assert "research_questions" in protocol
        assert "keywords" in protocol
        assert "screening" in protocol
        assert "sources" in protocol
        
        # With no API keys, should use fallback
        assert data["from_fallback"] is True


@pytest.mark.asyncio
async def test_draft_endpoint_validation():
    """Test draft endpoint input validation"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Too short subject text
        response = await client.post(
            "/draft",
            json={"subject_text": "short"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_refine_endpoint():
    """Test refine endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First get a draft protocol
        draft_response = await client.post(
            "/draft",
            json={
                "subject_text": "Impact of climate change on crop yields"
            }
        )
        protocol = draft_response.json()["protocol"]
        
        # Then refine it
        refine_response = await client.post(
            "/refine",
            json={"protocol": protocol}
        )
        assert refine_response.status_code == 200
        data = refine_response.json()
        
        assert "refinements" in data
        assert "from_fallback" in data
        
        refinements = data["refinements"]
        assert "inclusion_criteria_refined" in refinements
        assert "exclusion_criteria_refined" in refinements
        assert "borderline_examples" in refinements
        assert "risks_and_ambiguities" in refinements


@pytest.mark.asyncio
async def test_queries_endpoint():
    """Test queries endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get a protocol first
        draft_response = await client.post(
            "/draft",
            json={
                "subject_text": "Deep learning for medical imaging"
            }
        )
        protocol = draft_response.json()["protocol"]
        
        # Generate queries
        queries_response = await client.post(
            "/queries",
            json={"protocol": protocol}
        )
        assert queries_response.status_code == 200
        data = queries_response.json()
        
        assert "queries" in data
        assert "from_fallback" in data
        
        # Without API keys, queries list will be empty
        if data["from_fallback"]:
            assert len(data["queries"]) == 0


@pytest.mark.asyncio
async def test_freeze_endpoint():
    """Test freeze endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get a protocol first
        draft_response = await client.post(
            "/draft",
            json={
                "subject_text": "Artificial intelligence in healthcare"
            }
        )
        protocol = draft_response.json()["protocol"]
        
        # Freeze it
        freeze_response = await client.post(
            "/freeze",
            json={"protocol": protocol}
        )
        assert freeze_response.status_code == 200
        data = freeze_response.json()
        
        assert "protocol" in data
        assert "manifest" in data
        
        manifest = data["manifest"]
        assert "frozen_at_utc" in manifest
        assert "protocol_sha256" in manifest
        assert "source_files" in manifest
        assert "notes" in manifest
        
        # Check hash format (64 hex chars)
        assert len(manifest["protocol_sha256"]) == 64


@pytest.mark.asyncio
async def test_freeze_with_refinements():
    """Test freeze endpoint with refinements merged"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get protocol and refinements
        draft_response = await client.post(
            "/draft",
            json={
                "subject_text": "Renewable energy adoption patterns"
            }
        )
        protocol = draft_response.json()["protocol"]
        
        refine_response = await client.post(
            "/refine",
            json={"protocol": protocol}
        )
        refinements = refine_response.json()["refinements"]
        
        # Freeze with refinements
        freeze_response = await client.post(
            "/freeze",
            json={
                "protocol": protocol,
                "refinements": refinements
            }
        )
        assert freeze_response.status_code == 200
        data = freeze_response.json()
        
        # Check that refinements were merged
        frozen_protocol = data["protocol"]
        screening = frozen_protocol["screening"]
        
        # Should have refined criteria
        assert screening["inclusion_criteria"] == refinements["inclusion_criteria_refined"]
        assert screening["exclusion_criteria"] == refinements["exclusion_criteria_refined"]


@pytest.mark.asyncio
async def test_process_time_header():
    """Test that process time header is added to responses"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert "X-Process-Time-Ms" in response.headers
        
        # Should be a numeric value
        process_time = float(response.headers["X-Process-Time-Ms"])
        assert process_time >= 0


@pytest.mark.asyncio
async def test_cors_headers():
    """Test CORS headers are present"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers


# Integration test with custom model parameter
@pytest.mark.asyncio
async def test_custom_model_parameter():
    """Test that custom model parameter is accepted"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/draft",
            json={
                "subject_text": "Quantum computing applications in cryptography",
                "model": "gemini:gemini-1.5-pro"  # Custom model
            }
        )
        assert response.status_code == 200
        # Will still use fallback without API key, but should accept parameter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
