# Protocol Wizard API (FastAPI) - Enhanced Version

AI-powered systematic review protocol generation with robust LLM integration, retry logic, and comprehensive observability.

## 🚀 Key Features

### Core Functionality
- **Draft Generation**: Extract research protocol from subject text
- **Criteria Refinement**: Enhance inclusion/exclusion criteria with examples
- **Query Generation**: Create database-specific search queries
- **Protocol Freezing**: Cryptographic hashing for reproducibility

### Enhanced LLM Integration
- ✅ **Async/Await**: Non-blocking LLM calls for better performance
- ✅ **Retry Logic**: Exponential backoff with configurable attempts
- ✅ **Timeout Handling**: Configurable timeouts prevent hanging requests
- ✅ **Token Tracking**: Monitor usage and costs
- ✅ **Provider Health Checks**: Monitor LLM provider availability
- ✅ **Graceful Fallbacks**: Deterministic responses when LLMs fail
- ✅ **Structured Responses**: Typed LLMResponse with metadata

### Observability
- ✅ **Comprehensive Logging**: Structured logs for all operations
- ✅ **Request Timing**: Track latency for every endpoint
- ✅ **Error Tracking**: Detailed error messages with context
- ✅ **Health Endpoints**: Basic and detailed health checks

### Code Quality
- ✅ **Type Hints**: Full type coverage
- ✅ **Input Validation**: Pydantic validators for all inputs
- ✅ **Error Handling**: Specific exception handling, no bare excepts
- ✅ **Configuration**: Environment-based config management

## 📋 API Endpoints

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with LLM provider status
- `GET /schema` - Get protocol JSON schema

### Protocol Workflow
- `POST /draft` - Generate initial protocol from text
- `POST /refine` - Refine screening criteria
- `POST /queries` - Generate database queries
- `POST /freeze` - Freeze protocol with SHA-256 hash

## 🛠️ Installation

### 1. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Install LLM Providers (Optional)

```bash
# For Google Gemini
pip install google-generativeai>=0.7

# For OpenAI
pip install openai>=1.47
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DEFAULT_MODEL` | Default LLM model | `gemini:gemini-1.5-flash` |
| `LLM_MAX_RETRIES` | Max retry attempts | `3` |
| `LLM_TIMEOUT_SECONDS` | Request timeout | `60` |
| `LLM_BASE_DELAY` | Initial retry delay (seconds) | `1.0` |
| `LLM_MAX_DELAY` | Max retry delay (seconds) | `10.0` |
| `LLM_TEMPERATURE` | LLM temperature | `0.0` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Supported Models

**Google Gemini** (Recommended):
- `gemini:gemini-1.5-flash` - Fast, efficient
- `gemini:gemini-1.5-pro` - More capable

**OpenAI**:
- `openai:gpt-4o-mini` - Cost-effective
- `openai:gpt-4o` - Most capable

## 🚀 Running the Server

### Development

```bash
uvicorn server.main:app --reload --port 8000
```

### Production

```bash
# With Gunicorn for production
gunicorn server.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install LLM providers
RUN pip install google-generativeai openai

COPY . .

EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Example Usage

### Draft Protocol

```bash
curl -X POST http://localhost:8000/draft \
  -H "Content-Type: application/json" \
  -d '{
    "subject_text": "Effect of deep learning on crop disease detection in field conditions",
    "model": "gemini:gemini-1.5-flash"
  }'
```

### Health Check

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

## 🔍 What's New in v0.2.0

### LLM Integration Improvements
1. **Async Support**: All LLM calls now use async/await
2. **Retry Logic**: Exponential backoff with configurable retries
3. **Structured Responses**: `LLMResponse` dataclass with metadata
4. **Provider Abstraction**: Clean separation of OpenAI and Gemini
5. **Token Tracking**: Monitor usage and costs
6. **Better Error Messages**: Detailed error context

### API Improvements
1. **Request Logging**: All requests logged with timing
2. **Global Exception Handler**: Graceful error responses
3. **Health Endpoints**: Monitor LLM provider status
4. **Process Time Headers**: `X-Process-Time-Ms` header on all responses
5. **Enhanced Validation**: Pydantic validators on all models

### Code Quality
1. **Type Safety**: Full type hints coverage
2. **Better Error Handling**: No bare excepts
3. **Configuration Management**: Environment-based config
4. **Logging**: Structured logging throughout
5. **Startup/Shutdown Events**: Lifecycle management

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=server --cov-report=html

# Async tests
pytest -v tests/test_async.py
```

## 📝 Logging

Logs include:
- Request/response timing
- LLM call attempts and retries
- Token usage
- Error details with context
- Provider health status

Example log output:
```
2025-01-15 10:30:15 - server.llm - INFO - LLM call succeeded: provider=gemini, model=gemini-1.5-flash, latency=1234ms, attempt=1
2025-01-15 10:30:15 - server.main - INFO - Response: POST /draft status=200 time=1250.45ms
```

## 🔒 Security Considerations

1. **CORS**: Configure `ALLOWED_ORIGINS` appropriately for production
2. **API Keys**: Never commit `.env` file, use secrets management
3. **Rate Limiting**: Consider adding rate limiting middleware
4. **Input Validation**: All inputs validated with Pydantic
5. **Logging**: Sensitive data not logged

## 🐛 Troubleshooting

### LLM Calls Failing
1. Check API keys are set correctly
2. Verify provider status: `GET /health/detailed`
3. Check logs for detailed error messages
4. Ensure firewall/network allows API access

### Slow Response Times
1. Check `LLM_TIMEOUT_SECONDS` setting
2. Review `LLM_MAX_RETRIES` - reduce if too many retries
3. Consider using faster models (e.g., `gemini-1.5-flash`)
4. Check network latency to API providers

### Fallback Always Triggered
1. Verify API keys are valid
2. Check provider quotas/limits
3. Review logs for specific error messages
4. Test provider connectivity manually

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Google Gemini API](https://ai.google.dev/docs)
- [OpenAI API](https://platform.openai.com/docs)

## 🤝 Contributing

Improvements welcome! Focus areas:
- Additional LLM providers (Anthropic Claude, Cohere, etc.)
- Caching mechanisms for repeated queries
- Rate limiting and quota management
- Metrics and monitoring (Prometheus, etc.)
- Additional validation rules

## 📄 License

[Your License Here]