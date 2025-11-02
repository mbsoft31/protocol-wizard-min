Protocol Wizard API (FastAPI)

Endpoints
- GET /health: simple health check
- GET /schema: returns the protocol JSON schema
- POST /draft: { subject_text, model? } → protocol, checklist, from_fallback, validation
- POST /refine: { protocol, model? } → refinements, from_fallback
- POST /queries: { protocol, model? } → queries[], from_fallback
- POST /freeze: { protocol, refinements? } → protocol, manifest

LLM Integration
- Defaults to Gemini: set `GOOGLE_API_KEY` and (optionally) `DEFAULT_MODEL=gemini:gemini-1.5-flash`
- OpenAI is optional: set `OPENAI_API_KEY` and use `DEFAULT_MODEL=openai:gpt-4o-mini`
- If no keys or model call fails, draft/refine return deterministic fallbacks; queries returns empty list

Run
1) python -m pip install -r server/requirements.txt
2) uvicorn server.main:app --reload --port 8000

Env
- DEFAULT_MODEL (optional, defaults to `gemini:gemini-1.5-flash`)
- GOOGLE_API_KEY (optional, preferred)
- OPENAI_API_KEY (optional)
