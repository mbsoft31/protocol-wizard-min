# Protocol Wizard - Quickstart Guide

Get up and running in 5 minutes! ⚡

## 🚀 Quick Setup

### Option 1: Docker (Recommended)

**Prerequisites:** Docker and Docker Compose installed

```bash
# 1. Clone repository
git clone <your-repo>
cd protocol-wizard

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 3. Start services
docker-compose up -d

# 4. Verify it's running
curl http://localhost:8000/health
```

**That's it!** API is running at `http://localhost:8000`

---

### Option 2: Local Development

**Prerequisites:** Python 3.10+

```bash
# 1. Install dependencies
pip install -r server/requirements.txt
pip install openai google-generativeai  # LLM providers (optional)

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start server
uvicorn server.main:app --reload --port 8000

# 4. Test it
curl http://localhost:8000/health/detailed
```

---

## 🧪 First API Call

### Generate Your First Protocol

```bash
curl -X POST http://localhost:8000/draft \
  -H "Content-Type: application/json" \
  -d '{
    "subject_text": "Machine learning for predicting patient outcomes in ICU settings"
  }'
```

**Success!** You'll get a complete protocol with:
- ✅ Research questions
- ✅ PICOS framework
- ✅ Keywords and synonyms
- ✅ Screening criteria
- ✅ Data sources

---

## 🎯 Complete Workflow (2 minutes)

### Python Script

```python
import requests

API = "http://localhost:8000"

# 1. Draft protocol
protocol = requests.post(f"{API}/draft", json={
    "subject_text": "Impact of exercise on cognitive decline in elderly"
}).json()["protocol"]

# 2. Refine criteria
refinements = requests.post(f"{API}/refine", json={
    "protocol": protocol
}).json()["refinements"]

# 3. Generate queries
queries = requests.post(f"{API}/queries", json={
    "protocol": protocol
}).json()["queries"]

# 4. Freeze for reproducibility
frozen = requests.post(f"{API}/freeze", json={
    "protocol": protocol,
    "refinements": refinements
}).json()

print(f"✓ Protocol frozen!")
print(f"  Hash: {frozen['manifest']['protocol_sha256'][:16]}...")
print(f"  Queries: {len(queries)} databases")
```

---

## 🔧 Configuration

### Essential Settings

Edit `.env`:

```bash
# At minimum, set ONE of these:
GOOGLE_API_KEY=your_gemini_key_here     # Recommended (free tier available)
OPENAI_API_KEY=your_openai_key_here     # Alternative

# Optional: Choose model
DEFAULT_MODEL=gemini:gemini-1.5-flash   # Fast & cheap
# DEFAULT_MODEL=gemini:gemini-1.5-pro   # More capable
# DEFAULT_MODEL=openai:gpt-4o-mini      # OpenAI option
```

### Get API Keys

**Google Gemini (Free tier):**
1. Go to [https://ai.google.dev/](https://ai.google.dev/)
2. Click "Get API Key"
3. Create new key
4. Copy to `.env`

**OpenAI (Paid):**
1. Go to [https://platform.openai.com/](https://platform.openai.com/)
2. Create account
3. Add payment method
4. Generate API key
5. Copy to `.env`

---

## 🌐 Frontend Integration

### Enable CORS for Your App

Edit `.env`:

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### JavaScript/TypeScript Frontend

```javascript
// Configure API client
const API_BASE = 'http://localhost:8000';

// Make request
const response = await fetch(`${API_BASE}/draft`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    subject_text: 'Your research topic...'
  })
});

const result = await response.json();
console.log(result.protocol);
```

---

## 🔍 Verify Setup

### Health Check

```bash
curl http://localhost:8000/health/detailed
```

**Expected output:**
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

✅ `gemini: true` or `openai: true` means you're configured correctly!

---

## 📊 Enable Monitoring (Optional)

### Start with Metrics

```bash
# 1. Enable metrics in .env
ENABLE_METRICS=true

# 2. Start with monitoring stack
docker-compose --profile monitoring up -d

# 3. Access dashboards
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001 (admin/admin)
```

---

## 🐛 Troubleshooting

### "from_fallback: true" in responses

**Problem:** LLM not working, using fallback responses

**Solution:**
1. Check API key is set: `cat .env | grep API_KEY`
2. Verify key is valid at provider's website
3. Check health: `curl http://localhost:8000/health/detailed`

---

### CORS errors in browser

**Problem:** Frontend can't connect to API

**Solution:**
```bash
# Add your frontend origin to .env
ALLOWED_ORIGINS=http://localhost:3000

# Restart API
docker-compose restart api
# or
uvicorn server.main:app --reload
```

---

### Rate limit errors

**Problem:** "429 Too Many Requests"

**Solution:**
```bash
# Disable rate limiting in .env
ENABLE_RATE_LIMITING=false

# Or increase limits
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_BURST=20
```

---

### Connection refused

**Problem:** Can't connect to `localhost:8000`

**Solution:**
```bash
# Check if service is running
docker ps  # Docker
# or
ps aux | grep uvicorn  # Local

# Check if port is in use
lsof -i :8000

# Try different port
uvicorn server.main:app --port 8001
```

---

## 📚 Next Steps

1. **Read API Examples:** Check `api-examples.md` for detailed usage
2. **Customize Prompts:** Edit files in `prompts/` directory
3. **Add Tests:** Run `pytest` to verify everything works
4. **Deploy:** See `backend.md` for production deployment guide

---

## 🎓 Learn More

- **Full API Documentation:** `api-examples.md`
- **Deployment Guide:** `backend.md`
- **Migration Guide:** `migration-guide.md` (if upgrading)
- **Architecture:** `improvements-summary.md`

---

## 💡 Pro Tips

### Faster Responses
```bash
# Use flash model for speed
DEFAULT_MODEL=gemini:gemini-1.5-flash
LLM_TIMEOUT_SECONDS=30
```

### Better Quality
```bash
# Use pro model for quality
DEFAULT_MODEL=gemini:gemini-1.5-pro
LLM_MAX_RETRIES=5
```

### Debug Mode
```bash
# Enable verbose logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json  # Structured logs
```

### Production Ready
```bash
# Enable all safeguards
ENABLE_RATE_LIMITING=true
ENABLE_SIZE_LIMITING=true
ENABLE_METRICS=true
ALLOWED_ORIGINS=https://your-domain.com
```

---

## ✅ Quick Checklist

- [ ] API key configured
- [ ] Health check returns `"ok"`
- [ ] First protocol generated successfully
- [ ] CORS configured for your frontend
- [ ] Monitoring enabled (optional)
- [ ] Tests passing: `pytest`

**All done?** You're ready to build! 🎉

---

## 🆘 Need Help?

- **GitHub Issues:** Report bugs or request features
- **Documentation:** Check `api-examples.md` for detailed examples
- **Logs:** Check `docker-compose logs api` for errors

Happy protocol generation! 🚀

