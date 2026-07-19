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

Create or edit the repository-root `.env` file. It is excluded from Git.

Required shared settings:
- `MONGO_URI` - MongoDB connection string
- `MONGO_DB_NAME` - database name (default: `nie`)
- `LLM_BACKEND` - `anthropic`, `azure`, `openai`, or `ollama`
- `LLM_TIMEOUT_SECONDS` - request timeout recorded in `pipelineRuns.params`

For Azure Foundry v1:
- `AZURE_OPENAI_BASE_URL` - the base URL ending in `/openai/v1/`, not the
  complete `/chat/completions` URL
- `AZURE_OPENAI_MODEL` - the deployment name used in API requests
- `AZURE_OPENAI_API_KEY` - keep this only in `.env`; never commit it
- `AZURE_OPENAI_MODEL_VERSION` - the version shown by the deployment
- `AZURE_OPENAI_DEPLOYMENT_TYPE` - the deployment type shown by Foundry

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
