# Thematic Clusters — NHS Survey Analysis Tool

An AI-assisted qualitative analysis tool built on the [Neighbourhood Insight Engine (NIE)](https://github.com/RichardGomer/NIE-prototype). Upload an NHS survey CSV, let the AI pipeline cluster and label the responses into themes, then explore and deliberate on them in an interactive graph and canvas workspace.

---

## Architecture

```
Browser (React + Vite)  →  Express RPC API (Node.js)  →  MongoDB Atlas
                        →  Python FastAPI AI service   →  MongoDB Atlas
```

| Service | Port | Directory |
|---|---|---|
| React frontend | 5173 | `react-client/` |
| Node.js API | 3000 | `api-server/` |
| Python AI service | 8000 | `ai-service/` |

---

## Requirements

- **Node.js** 18+
- **Python** 3.11+
- **MongoDB Atlas** account (free tier is fine) — or a local MongoDB instance
- **Anthropic API key** (for cluster labelling via Claude)

---

## Setup

### 1. Environment variables

Create a `.env` file in the **root of this repo** (next to `react-client/`, `api-server/`, `ai-service/`):

```env
# MongoDB
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?appName=Cluster0
MONGO_DB_NAME=nie

# LLM backend — anthropic | openai | ollama
LLM_BACKEND=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6

# Optional — only needed if LLM_BACKEND=openai
OPENAI_API_KEY=sk-...

# Optional — only needed if LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Create a `.env.local` file inside `react-client/`:

```env
VITE_API_URI=http://localhost:3000
VITE_AI_URI=http://localhost:8000
```

### 2. Node dependencies

```bash
cd react-client
npm install
```

### 3. Python virtual environment

```bash
cd ai-service
python -m venv venv

# Windows
venv\Scripts\pip install -r requirements.txt
python -m spacy download en_core_web_sm

# macOS / Linux
venv/bin/pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## Running

Start all three services with one command from `react-client/`:

```bash
cd react-client
npm run dev:all
```

Then open **http://localhost:5173** in your browser.

To start services individually:

```bash
# React frontend
npm run dev

# Node.js API
npm run api

# Python AI service
npm run ai
```

---

## Usage

### Analysing a survey

1. Go to **Survey Ingestion** in the sidebar
2. Upload a CSV or XLSX file (one row per response, one column per question)
3. Set a survey name and minimum cluster size (default 5; lower = more clusters)
4. Click **Run Pipeline** — four steps run automatically:
   - **Parsing & PII Redaction** — spaCy removes names and dates
   - **Embedding Responses** — sentence-transformers encodes each response
   - **Discovering Clusters** — UMAP + HDBSCAN groups similar responses
   - **Labelling Clusters** — Claude names each theme
5. Click **View Cluster Graph** to explore results

### Cluster Graph

- Large coloured nodes = theme clusters (labelled by Claude)
- Small nodes = individual survey responses
- Hover any node to read its content
- Click a theme node to open it in a Virtual Floor workspace

### Virtual Floor

- Drag-and-drop canvas for deliberating on a cluster's responses
- Right panel: add more fragments, create colour-coded annotations
- Save named workspaces to MongoDB and reload them later

### Other tools

- **Document Viewer** — upload and browse HTML documents
- **Fragment Extractors** — manually extract fragments from documents by text section, CSS query, or image crop
- **My Fragments** — browse all saved fragments across all documents

---

## Demo dataset

A ready-to-use synthetic NHS inpatient survey is included:

```
demo_nhs_survey_v2.csv
```

30 responses across 5 questions covering themes like discharge planning, pain management, staff communication, end-of-life care, and infection control.
