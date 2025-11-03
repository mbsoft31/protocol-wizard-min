# Migration Guide: v0.1.0 → v0.2.0

This guide helps you upgrade from the original Protocol Wizard API to the enhanced version with improved LLM integration and observability.

## 🎯 What Changed

### Breaking Changes
✅ **None!** The API is backward compatible. All existing endpoints work the same way.

### New Features
- Async LLM calls with retry logic
- Token usage tracking
- Detailed health endpoint
- Request timing headers
- Enhanced logging
- Better error handling

## 📦 Installation Updates

### 1. Update Requirements

The base requirements are compatible. If you're using LLM providers, update them:

```bash
# For async OpenAI support
pip install --upgrade openai>=1.47

# For latest Gemini
pip install --upgrade google-generativeai>=0.7
```

### 2. Add New Dependencies (Optional)

For testing the async endpoints:

```bash
pip install pytest-asyncio>=0.23 httpx>=0.27
```

## ⚙️ Configuration Changes

### New Environment Variables

Add these to your `.env` file (all optional):

```bash
# LLM Retry Configuration (new)
LLM_MAX_RETRIES=3
LLM_TIMEOUT_SECONDS=60
LLM_BASE_DELAY=1.0
LLM_MAX_DELAY=10.0
LLM_TEMPERATURE=0.0

# CORS Configuration (enhanced)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO
```

### Existing Variables (unchanged)
```bash
GOOGLE_API_KEY=your_key
OPENAI_API_KEY=your_key
DEFAULT_MODEL=gemini:gemini-1.5-flash
```

## 🔄 Code Migration

### If You're Importing the Module

#### Old Code (still works):
```python
from server.llm import call_llm

result = call_llm("your prompt", model="gemini:gemini-1.5-flash")
```

#### New Code (recommended):
```python
from server.llm import call_llm_async, LLMConfig
import asyncio

async def main():
    config = LLMConfig(max_retries=3, timeout_seconds=60)
    response = await call_llm_async(
        "your prompt",
        model="gemini:gemini-1.5-flash",
        config=config
    )
    
    if response.success:
        print(f"Content: {response.content}")
        print(f"Tokens: {response.tokens_used}")
        print(f"Latency: {response.latency_ms}ms")
    else:
        print(f"Error: {response.error}")

asyncio.run(main())
```

### Response Structure Changes

#### LLM Responses

**Old**: Returns `Optional[str]` or `None`
```python
result = call_llm("prompt")
if result is None:
    # LLM failed
```

**New**: Returns structured `LLMResponse` with metadata
```python
response = await call_llm_async("prompt")
if response.success:
    content = response.content
    tokens = response.tokens_used
    latency = response.latency_ms
else:
    error = response.error
```

#### API Responses

All API responses now include timing information in headers:

```python
# Client code
response = requests.post("http://localhost:8000/draft", json=data)
process_time_ms = response.headers.get("X-Process-Time-Ms")
print(f"Request took {process_time_ms}ms")
```

## 🆕 New Endpoints

### Detailed Health Check

Monitor LLM provider status:

```bash
curl http://localhost:8000/health/detailed
```

Response:
```json
{
  "status": "ok",
  "llm_providers": {
    "gemini": true,
    "openai": false
  },
  "default_model": "gemini:gemini-1.5-flash"
}
```

Use this to:
- Check if your API keys are working
- Monitor which providers are available
- Debug configuration issues

## 📊 Observability Improvements

### Logging

The new version logs much more detail:

```python
# Old: minimal logging
# New: structured logs with context

2025-01-15 10:30:15 - server.main - INFO - Request: POST /draft from 127.0.0.1
2025-01-15 10:30:16 - server.llm - INFO - LLM call succeeded: provider=gemini, latency=1234ms
2025-01-15 10:30:16 - server.main - INFO - Response: POST /draft status=200 time=1250ms
```

### Metrics

Response headers now include timing:

```
X-Process-Time-Ms: 1250
```

Track these in your monitoring:
```python
import requests
import time

def track_request_time(endpoint, data):
    start = time.time()
    response = requests.post(endpoint, json=data)
    client_time = (time.time() - start) * 1000
    server_time = float(response.headers.get("X-Process-Time-Ms", 0))
    
    print(f"Client time: {client_time:.2f}ms")
    print(f"Server time: {server_time:.2f}ms")
    print(f"Network overhead: {client_time - server_time:.2f}ms")
```

## 🧪 Testing Updates

### Running Tests

```bash
# Old tests still work
pytest

# New async tests
pytest tests/test_async_endpoints.py -v

# With coverage
pytest --cov=server --cov-report=html
```

### Writing Tests

#### Old Style (still works):
```python
def test_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
```

#### New Style (recommended for async):
```python
@pytest.mark.asyncio
async def test_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
```

## 🚀 Performance Impact

### Expected Improvements

1. **Response Times**: Similar or slightly better due to async I/O
2. **Throughput**: Better under concurrent load (async advantage)
3. **Reliability**: Improved due to retry logic

### Potential Issues

1. **First Request Slower**: Event loop initialization overhead
2. **Memory Usage**: Slightly higher due to async machinery
3. **CPU Usage**: May increase slightly under high concurrency

### Monitoring

Add this to track performance:

```python
import logging
import time

logger = logging.getLogger(__name__)

@app.middleware("http")
async def performance_logging(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    
    logger.info(f"{request.method} {request.url.path} - {duration:.2f}ms")
    return response
```

## 🔧 Troubleshooting

### Issue: "asyncio.run() cannot be called from a running event loop"

**Solution**: You're trying to use sync wrapper in async context

```python
# Don't do this in async code
result = call_llm("prompt")  # Uses asyncio.run() internally

# Do this instead
result = await call_llm_async("prompt")
```

### Issue: "No module named 'openai'"

**Solution**: Install the async-compatible OpenAI package

```bash
pip install openai>=1.47
```

### Issue: Import errors after upgrade

**Solution**: Restart your Python process/server

```bash
# Stop uvicorn
# Then restart
uvicorn server.main:app --reload --port 8000
```

### Issue: Tests failing with async errors

**Solution**: Install pytest-asyncio

```bash
pip install pytest-asyncio
```

Add to `pytest.ini` or `pyproject.toml`:
```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## ✅ Migration Checklist

- [ ] Update Python packages: `pip install -r requirements.txt`
- [ ] Install LLM providers: `pip install openai google-generativeai`
- [ ] Copy `.env.example` to `.env` and configure
- [ ] Add new environment variables (optional)
- [ ] Update CORS settings for production
- [ ] Run health check: `curl http://localhost:8000/health/detailed`
- [ ] Update any custom code to use async functions
- [ ] Update tests to use pytest-asyncio
- [ ] Review and update monitoring/logging
- [ ] Test all endpoints with your data
- [ ] Deploy to staging and test
- [ ] Update documentation for your team

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: Look for detailed error messages
2. **Health check**: Use `/health/detailed` to debug
3. **Test providers**: Verify API keys work directly
4. **Review config**: Ensure environment variables are set
5. **Consult README**: Check the enhanced README.md

## 📈 Gradual Migration Path

You can migrate gradually:

1. **Phase 1**: Deploy new code, keep using old patterns
2. **Phase 2**: Add new health check monitoring
3. **Phase 3**: Update client code to check timing headers
4. **Phase 4**: Migrate internal code to async patterns
5. **Phase 5**: Implement advanced features (caching, etc.)

The new version is designed to be fully backward compatible, so you can upgrade at your own pace!