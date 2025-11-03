import pytest
from httpx import AsyncClient, ASGITransport

from protocol_api.main import app
from protocol_api.utils import canonical_json_string, sha256_text


@pytest.mark.asyncio
async def test_frontend_backend_hash_alignment():
    """
    Two-part check:
    1) Canonicalization of a simple dict produces expected exact string.
    2) For a valid Protocol payload, /freeze manifest hash equals backend hash.
    """
    simple_obj = {
        "sources": ["arxiv", "pubmed"],
        "screening": {
            "years": [2020, 2025],
            "languages": ["en", "fr"],
        },
        "keywords": {
            "include": ["AI", "ML"],
            "exclude": ["robotics"],
        },
    }

    # Part 1: canonical string check (mirrors frontend expectation)
    backend_canonical = canonical_json_string(simple_obj)
    expected_canonical = (
        '{"keywords":{"exclude":["robotics"],"include":["AI","ML"]},'
        '"screening":{"languages":["en","fr"],"years":[2020,2025]},'
        '"sources":["arxiv","pubmed"]}'
    )
    assert backend_canonical == expected_canonical

    # Part 2: valid Protocol round-trip via /freeze
    protocol_data = {
        "research_questions": ["How does X affect Y?"],
        "keywords": {
            "include": ["AI", "ML"],
            "exclude": ["robotics"],
        },
        "screening": {
            "inclusion_criteria": ["Has ML method"],
            "exclusion_criteria": ["Review paper"],
            "years": [2020, 2025],
            "languages": ["en"],
            "doc_types": ["journal"],
        },
        "sources": ["arxiv", "pubmed"],
    }

    # Hash directly from plain dict
    local_hash = sha256_text(canonical_json_string(protocol_data))

    # Hash from Pydantic-normalized model (what the API uses internally)
    from protocol_api.models import Protocol as ProtocolModel
    normalized = ProtocolModel.model_validate(protocol_data).model_dump()
    normalized_hash = sha256_text(canonical_json_string(normalized))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/freeze", json={"protocol": protocol_data})
        assert response.status_code == 200
        api_hash = response.json()["manifest"]["protocol_sha256"]
        # API hash should match the normalized hash
        assert api_hash == normalized_hash
