from __future__ import annotations
import os
import json
from typing import Optional


def call_llm(prompt: str, model: str = "gemini:gemini-1.5-flash") -> Optional[str]:
    """
    Attempt to call Google Gemini (default) or OpenAI depending on model prefix.
    Environment:
      - OPENAI_API_KEY
      - GOOGLE_API_KEY
    Returns text or None on failure (caller should fallback).
    """
    vendor, name = (model.split(":", 1) + [""])[:2] if ":" in model else ("openai", model)

    # OpenAI
    if vendor == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            msg = client.chat.completions.create(
                model=name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return msg.choices[0].message.content
        except Exception:
            return None

    # Gemini
    if vendor in ("gemini", "google") and os.getenv("GOOGLE_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model_g = genai.GenerativeModel(name)
            resp = model_g.generate_content(prompt)
            # Some SDK versions expose text as .text
            if hasattr(resp, "text"):
                return resp.text  # type: ignore[attr-defined]
            # Fallback attempt: concatenate parts if present
            try:
                return "".join([p.text for p in getattr(resp, "candidates", []) for p in getattr(p, "content", {}).get("parts", [])])
            except Exception:
                return None
        except Exception:
            return None

    return None


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

FALLBACK_REFINEMENTS = json.dumps(
    {
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
    }
)
