# NIE AI Service

Python/FastAPI microservice that handles the AI pipeline for the NHS survey analysis tool.

## Setup

### 1. Prerequisites
- Python 3.11+
- A MongoDB Atlas cluster (free M0 tier is fine)

### 2. Create and activate virtual environment
```bash
cd ai-service
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download the spaCy model
```bash
python -m spacy download en_core_web_sm
```

### 5. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- `MONGO_URI` — your Atlas connection string (same one used by the NIE api-server)
- `MONGO_DB_NAME` — database name (default: `nie`)
- `LLM_BACKEND` — `openai` or `ollama`
- `OPENAI_API_KEY` — if using OpenAI

### 6. Run the service
```bash
uvicorn main:app --reload --port 8000
```

The API docs will be available at http://localhost:8000/docs

---

## Pipeline endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/ingest/survey` | POST | Upload CSV/XLSX → redact PII → write fragments to MongoDB |
| `/embed/fragments` | POST | Embed fragment text with sentence-transformers |
| `/cluster/run` | POST | Run UMAP + HDBSCAN → create cluster documents |
| `/label/clusters` | POST | Label clusters with LLM |
| `/cluster/{id}/graph-data` | GET | Get Sigma.js-ready graph data for a cluster |
| `/feedback/recluster` | POST | Record a manual re-coding event |

## Running the full pipeline (manual test)

```bash
# 1. Ingest
curl -X POST http://localhost:8000/ingest/survey \
  -F "file=@my_survey.csv" \
  -F "survey_name=NHS Ward Survey 2024"

# 2. Embed (use doc_id from step 1)
curl -X POST http://localhost:8000/embed/fragments \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "<doc_id>"}'

# 3. Cluster
curl -X POST http://localhost:8000/cluster/run \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "<doc_id>", "min_cluster_size": 5}'

# 4. Label (use cluster_ids from step 3)
curl -X POST http://localhost:8000/label/clusters \
  -H "Content-Type: application/json" \
  -d '{"cluster_ids": ["<id1>", "<id2>"]}'
```
