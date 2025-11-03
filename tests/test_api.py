from __future__ import annotations
import os
from fastapi.testclient import TestClient

from protocol_api.main import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_draft_refine_queries_freeze_fallback_flow():
    # Ensure default model is Gemini; env may override
    if "DEFAULT_MODEL" in os.environ:
        del os.environ["DEFAULT_MODEL"]

    # 1) Draft
    dr = client.post("/draft", json={"subject_text": "Test subject about lab-to-field generalization."})
    assert dr.status_code == 200
    djson = dr.json()
    assert djson["from_fallback"] is True  # No keys in CI => fallback path
    assert djson["validation"]["valid"] is True
    protocol = djson["protocol"]

    # 2) Refine
    rr = client.post("/refine", json={"protocol": protocol})
    assert rr.status_code == 200
    rjson = rr.json()
    assert rjson["from_fallback"] is True
    refinements = rjson["refinements"]
    assert "inclusion_criteria_refined" in refinements

    # 3) Queries (no fallback dataset => expect empty list)
    qr = client.post("/queries", json={"protocol": protocol})
    assert qr.status_code == 200
    qjson = qr.json()
    assert qjson["from_fallback"] is True
    assert isinstance(qjson["queries"], list)

    # 4) Freeze — hash stable and 64 hex chars
    fr1 = client.post("/freeze", json={"protocol": protocol, "refinements": refinements})
    fr2 = client.post("/freeze", json={"protocol": protocol, "refinements": refinements})
    assert fr1.status_code == fr2.status_code == 200
    f1, f2 = fr1.json(), fr2.json()
    h1 = f1["manifest"]["protocol_sha256"]
    h2 = f2["manifest"]["protocol_sha256"]
    assert h1 == h2
    assert isinstance(h1, str) and len(h1) == 64
