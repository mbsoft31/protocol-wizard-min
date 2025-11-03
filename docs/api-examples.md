# Protocol Wizard API - Usage Examples

Complete examples for every endpoint with curl, Python, and JavaScript.

## Table of Contents
- [Authentication](#authentication)
- [Health Checks](#health-checks)
- [Schema](#schema)
- [Draft Protocol](#draft-protocol)
- [Refine Criteria](#refine-criteria)
- [Generate Queries](#generate-queries)
- [Freeze Protocol](#freeze-protocol)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## Authentication

**No authentication required** - this is a public API. For production, consider adding API keys.

---

## Health Checks

### Basic Health Check

**Endpoint:** `GET /health`

**Description:** Quick health check for load balancers and monitoring.

#### cURL
```bash
curl http://localhost:8000/health
```

#### Python
```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
# {"status": "ok"}
```

#### JavaScript
```javascript
const response = await fetch('http://localhost:8000/health');
const data = await response.json();
console.log(data);
// {status: "ok"}
```

---

### Detailed Health Check

**Endpoint:** `GET /health/detailed`

**Description:** Check LLM provider availability and configuration.

#### cURL
```bash
curl http://localhost:8000/health/detailed
```

#### Response
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

#### Python
```python
response = requests.get("http://localhost:8000/health/detailed")
health = response.json()

if health["llm_providers"]["gemini"]:
    print("Gemini is available ✓")
```

---

## Schema

**Endpoint:** `GET /schema`

**Description:** Get the JSON Schema for protocol validation.

#### cURL
```bash
curl http://localhost:8000/schema | jq .
```

#### Python - Validate Against Schema
```python
import requests
import jsonschema

# Get schema
schema = requests.get("http://localhost:8000/schema").json()

# Validate your protocol
protocol = {
    "research_questions": ["How does X affect Y?"],
    "keywords": {
        "include": ["machine learning"],
        "exclude": []
    },
    # ... rest of protocol
}

try:
    jsonschema.validate(protocol, schema)
    print("Protocol is valid ✓")
except jsonschema.ValidationError as e:
    print(f"Invalid protocol: {e.message}")
```

---

## Draft Protocol

**Endpoint:** `POST /draft`

**Description:** Generate initial protocol from subject description.

### Request Body
```json
{
  "subject_text": "Your research topic description",
  "model": "gemini:gemini-1.5-flash"  // optional
}
```

### Example 1: Basic Usage

#### cURL
```bash
curl -X POST http://localhost:8000/draft \
  -H "Content-Type: application/json" \
  -d '{
    "subject_text": "Investigate the impact of deep learning models on crop disease detection accuracy when deployed in real-world field conditions versus controlled laboratory environments."
  }'
```

#### Python
```python
import requests

subject = """
Investigate the impact of deep learning models on crop disease detection 
accuracy when deployed in real-world field conditions versus controlled 
laboratory environments.
"""

response = requests.post(
    "http://localhost:8000/draft",
    json={"subject_text": subject}
)

result = response.json()
protocol = result["protocol"]
print(f"Generated {len(protocol['research_questions'])} research questions")
print(f"Used fallback: {result['from_fallback']}")
```

#### JavaScript
```javascript
const subject = `
Investigate the impact of deep learning models on crop disease detection 
accuracy when deployed in real-world field conditions versus controlled 
laboratory environments.
`;

const response = await fetch('http://localhost:8000/draft', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({subject_text: subject})
});

const result = await response.json();
console.log(result.protocol);
```

### Example 2: With Custom Model

#### Python
```python
response = requests.post(
    "http://localhost:8000/draft",
    json={
        "subject_text": subject,
        "model": "openai:gpt-4o"  # Use OpenAI instead
    }
)
```

### Response
```json
{
  "protocol": {
    "research_questions": [
      "How do deep learning models generalize from laboratory to field conditions?"
    ],
    "picos": {
      "population": ["crop plants"],
      "intervention": ["deep learning detection"],
      "comparison": ["lab vs field environments"],
      "outcomes": ["detection accuracy"],
      "context": ["agricultural field conditions"]
    },
    "keywords": {
      "include": ["plant disease detection", "deep learning", "field conditions"],
      "exclude": ["yield prediction", "irrigation"],
      "synonyms": {
        "domain shift": ["dataset shift", "external validity"]
      }
    },
    "screening": {
      "inclusion_criteria": [
        "Studies using deep learning for plant disease detection",
        "Includes field deployment or lab-to-field evaluation"
      ],
      "exclusion_criteria": [
        "Studies focused solely on yield prediction",
        "Pure simulation studies without field validation"
      ],
      "years": [2015, 2025],
      "languages": ["en"],
      "doc_types": ["journal", "conference", "preprint"]
    },
    "sources": ["openalex", "crossref", "pubmed", "arxiv"]
  },
  "checklist": "# HIL Checklist...",
  "from_fallback": false,
  "validation": {
    "valid": true,
    "errors": []
  }
}
```

---

## Refine Criteria

**Endpoint:** `POST /refine`

**Description:** Refine inclusion/exclusion criteria with examples and risk assessment.

### Request Body
```json
{
  "protocol": { /* protocol object from /draft */ },
  "model": "gemini:gemini-1.5-flash"  // optional
}
```

### Example

#### Python
```python
# First, get a draft protocol
draft_response = requests.post(
    "http://localhost:8000/draft",
    json={"subject_text": "Machine learning for medical diagnosis"}
)
protocol = draft_response.json()["protocol"]

# Then refine it
refine_response = requests.post(
    "http://localhost:8000/refine",
    json={"protocol": protocol}
)

refinements = refine_response.json()["refinements"]
print("Refined inclusion criteria:")
for criterion in refinements["inclusion_criteria_refined"]:
    print(f"  - {criterion}")

print("\nBorderline examples:")
for example in refinements["borderline_examples"]:
    print(f"  {example['text']}: {example['suggested']}")
    print(f"    Why: {example['why']}")
```

### Response
```json
{
  "refinements": {
    "inclusion_criteria_refined": [
      "Study uses supervised or semi-supervised ML for medical diagnosis",
      "Includes clinical validation or real patient data"
    ],
    "exclusion_criteria_refined": [
      "Pure theoretical ML models without clinical application",
      "Studies using only synthetic or simulated data"
    ],
    "borderline_examples": [
      {
        "text": "Study using ML on anonymized patient records without prospective validation",
        "suggested": "MAYBE",
        "why": "Has real data but lacks prospective validation"
      }
    ],
    "risks_and_ambiguities": [
      "Definition of 'medical diagnosis' may be ambiguous",
      "Risk of excluding relevant preprocessing techniques"
    ]
  },
  "from_fallback": false
}
```

---

## Generate Queries

**Endpoint:** `POST /queries`

**Description:** Generate database-specific search queries.

### Request Body
```json
{
  "protocol": { /* protocol object */ },
  "model": "gemini:gemini-1.5-flash"  // optional
}
```

### Example

#### Python
```python
# Generate queries from protocol
queries_response = requests.post(
    "http://localhost:8000/queries",
    json={"protocol": protocol}
)

queries = queries_response.json()["queries"]

for query in queries:
    print(f"\n{query['provider']} Query:")
    print(f"Family: {query['family']}")
    print(f"Rationale: {query['rationale']}")
    print(f"Native query: {query['native']}")
```

#### JavaScript
```javascript
const response = await fetch('http://localhost:8000/queries', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({protocol})
});

const {queries} = await response.json();

queries.forEach(query => {
  console.log(`${query.provider}:`, query.native);
});
```

### Response
```json
{
  "queries": [
    {
      "family": "openalex",
      "provider": "openalex-api",
      "native": {
        "search": "machine learning AND medical diagnosis AND clinical validation",
        "filter": {
          "publication_year": ">2015",
          "type": "article|preprint"
        }
      },
      "budget": {
        "max_results": 5000,
        "estimated_time": "5-10 minutes"
      },
      "rationale": "OpenAlex provides comprehensive coverage of scholarly literature"
    },
    {
      "family": "pubmed",
      "provider": "ncbi-entrez",
      "native": {
        "query": "(machine learning[Title/Abstract]) AND (medical diagnosis[MeSH Terms]) AND (clinical[All Fields])",
        "filters": {
          "mindate": "2015/01/01",
          "maxdate": "2025/12/31"
        }
      },
      "budget": {
        "max_results": 2000
      },
      "rationale": "PubMed for biomedical literature with MeSH terms"
    }
  ],
  "from_fallback": false
}
```

---

## Freeze Protocol

**Endpoint:** `POST /freeze`

**Description:** Freeze protocol with SHA-256 hash for reproducibility.

### Request Body
```json
{
  "protocol": { /* protocol object */ },
  "refinements": { /* optional refinements to merge */ }
}
```

### Example 1: Freeze Without Refinements

#### Python
```python
freeze_response = requests.post(
    "http://localhost:8000/freeze",
    json={"protocol": protocol}
)

result = freeze_response.json()
manifest = result["manifest"]

print(f"Frozen at: {manifest['frozen_at_utc']}")
print(f"SHA-256: {manifest['protocol_sha256']}")
print(f"\nInclude this hash in your PRISMA methods section:")
print(f"Protocol hash: {manifest['protocol_sha256']}")
```

### Example 2: Freeze With Refinements

#### Python
```python
# Merge refinements before freezing
freeze_response = requests.post(
    "http://localhost:8000/freeze",
    json={
        "protocol": protocol,
        "refinements": refinements  # Will merge refined criteria
    }
)

frozen = freeze_response.json()
print("Final frozen protocol ready for data harvesting!")
```

### Response
```json
{
  "protocol": { /* final protocol with refinements merged */ },
  "manifest": {
    "frozen_at_utc": "2025-01-15T10:30:45.123456Z",
    "protocol_sha256": "a1b2c3d4e5f6...789", 
    "source_files": ["inline"],
    "notes": "Freeze before data harvesting; include this hash in PRISMA/methods."
  }
}
```

---

## Error Handling

### Validation Errors

#### Example: Empty Subject Text
```python
response = requests.post(
    "http://localhost:8000/draft",
    json={"subject_text": ""}
)

if response.status_code == 422:
    error = response.json()
    print(f"Validation error: {error['detail']}")
```

### Rate Limiting

#### Example: Too Many Requests
```python
response = requests.post("http://localhost:8000/draft", json=data)

if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    print(f"Rate limited. Retry after {retry_after} seconds")
    time.sleep(int(retry_after))
    # Retry request
```

### Server Errors

#### Example: Handle Gracefully
```python
try:
    response = requests.post("http://localhost:8000/draft", json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.Timeout:
    print("Request timed out")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

---

## Rate Limiting

When rate limiting is enabled:

```python
import time
import requests

def make_request_with_retry(url, data, max_retries=3):
    """Make request with exponential backoff"""
    for attempt in range(max_retries):
        response = requests.post(url, json=data)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")

# Usage
response = make_request_with_retry(
    "http://localhost:8000/draft",
    {"subject_text": "..."}
)
```

---

## Complete Workflow Example

### Python

```python
import requests
import json

API_BASE = "http://localhost:8000"

def complete_protocol_workflow(subject_text: str) -> dict:
    """Complete protocol creation workflow"""
    
    # 1. Draft protocol
    print("1. Drafting protocol...")
    draft = requests.post(
        f"{API_BASE}/draft",
        json={"subject_text": subject_text}
    ).json()
    
    protocol = draft["protocol"]
    print(f"   ✓ Generated {len(protocol['research_questions'])} research questions")
    
    # 2. Refine criteria
    print("2. Refining criteria...")
    refinements = requests.post(
        f"{API_BASE}/refine",
        json={"protocol": protocol}
    ).json()["refinements"]
    
    print(f"   ✓ Generated {len(refinements['borderline_examples'])} borderline examples")
    
    # 3. Generate queries
    print("3. Generating database queries...")
    queries = requests.post(
        f"{API_BASE}/queries",
        json={"protocol": protocol}
    ).json()["queries"]
    
    print(f"   ✓ Generated {len(queries)} database queries")
    
    # 4. Freeze protocol
    print("4. Freezing protocol...")
    frozen = requests.post(
        f"{API_BASE}/freeze",
        json={
            "protocol": protocol,
            "refinements": refinements
        }
    ).json()
    
    manifest = frozen["manifest"]
    print(f"   ✓ Frozen with hash: {manifest['protocol_sha256'][:16]}...")
    
    return {
        "protocol": frozen["protocol"],
        "refinements": refinements,
        "queries": queries,
        "manifest": manifest
    }

# Run workflow
result = complete_protocol_workflow("""
Systematic review of machine learning applications in early detection 
of Alzheimer's disease using neuroimaging data.
""")

# Save results
with open("protocol_package.json", "w") as f:
    json.dump(result, f, indent=2)

print("\n✓ Complete protocol package saved!")
```

---

## Monitoring Request Performance

### Track Latency

```python
import requests
import time

start = time.time()
response = requests.post(
    "http://localhost:8000/draft",
    json={"subject_text": "..."}
)
client_latency = (time.time() - start) * 1000

# Server-side processing time
server_latency = float(response.headers.get("X-Process-Time-Ms", 0))

print(f"Client latency: {client_latency:.2f}ms")
print(f"Server latency: {server_latency:.2f}ms")
print(f"Network overhead: {client_latency - server_latency:.2f}ms")
```

---

## Request Tracing

### Correlate Requests

```python
import uuid

request_id = str(uuid.uuid4())

response = requests.post(
    "http://localhost:8000/draft",
    json={"subject_text": "..."},
    headers={"X-Request-ID": request_id}
)

# Server returns same ID
assert response.headers["X-Request-ID"] == request_id
print(f"Request traced with ID: {request_id}")
```

This allows you to correlate client requests with server logs.