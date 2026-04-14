# Thematic Clusters — NHS Survey Analysis Tool

A web application for qualitative analysis of NHS survey data. Researchers upload a CSV or Excel file of survey responses, and the tool helps them discover and organise thematic clusters using a combination of AI pipelines and interactive manual grouping.

---

## How it works

Three services run together to form the application:

- **React frontend** (port 5173) — the UI where researchers upload files, choose a pipeline, and interact with results
- **Node.js API server** (port 3000) — a thin Express layer handling document, fragment, and cluster reads/writes to MongoDB
- **Python AI service** (port 8000) — a FastAPI service that handles file parsing, text embedding, ML clustering, LLM calls, and placement suggestions

The core concept is **fragments**: each cell in a survey response becomes its own independently-clusterable unit. For example, if a row has columns for *Overall Experience*, *Staff Attitude*, and *Communication*, each answer becomes a separate fragment. Fragments are stored in MongoDB with their original text, a PII-redacted version, and (after embedding) a 384-dimensional semantic vector.

From there, researchers choose one of four pipelines to group fragments into thematic clusters.

---

## The four pipelines

### 1. Auto
The fully automated ML pipeline. After uploading and embedding, UMAP reduces the 384-dimensional embeddings to 10 dimensions, then HDBSCAN finds natural cluster boundaries without needing a target number of clusters. A second UMAP pass produces 2D coordinates for the graph visualisation. Each cluster is then named and summarised by an LLM. Best for large datasets where you want a fast first pass with no manual input.

### 2. Manual
An interactive drag-and-drop whiteboard built with React Flow. Fragments appear in a queue on the left; the researcher drags each one onto the canvas and physically groups them by proximity. Two fragments within 220px of each other are treated as part of the same group.

Once at least one other group has two or more members, the AI begins offering **cosine similarity suggestions** — it computes the distance between the dropped fragment's embedding and the centroid of each existing group and suggests the best match.

A **Sanity Check** also runs automatically after each drop: Claude reads sample texts from all groups and checks whether the placement makes sense. If it finds a clearly better group, an animated purple arrow appears pointing from the fragment to the suggested destination, with a tick (accept and move) and a cross (dismiss) button.

### 3. LLM Semantic
A fully automated LLM-driven pipeline. The researcher provides a **research question** (e.g. *"What themes emerge from female patients aged 20–50?"*) and optional **column filters** (case-insensitive substring matches on any CSV column, e.g. filtering the Gender column to "Female"). Claude then:
1. Filters out fragments that don't pass the column conditions
2. Filters out fragments that aren't semantically relevant to the research question
3. Reads each surviving fragment and either assigns it to an existing named cluster or creates a new one

Progress streams live to the UI as each fragment is processed. Results are saved to MongoDB as labelled cluster documents.

### 4. LLM Manual
The same drag-and-drop whiteboard as Manual, but the post-placement group suggestion uses Claude instead of cosine similarity. Claude reads up to four sample texts from each existing group and decides which group the queued fragment fits best, or whether a new group is needed. Accepts a research question to focus suggestions. The Sanity Check feature works here too.

---

## Why these design choices

**Per-question fragments** — a single survey row often contains answers to several unrelated questions. Treating the full row as one unit mixes themes and produces poor clusters. Splitting by column means each fragment carries one coherent idea.

**UMAP + HDBSCAN for Auto** — UMAP preserves local neighbourhood structure better than PCA when reducing high-dimensional embeddings, and HDBSCAN discovers cluster count automatically, making the pipeline genuinely exploratory rather than requiring the researcher to guess a target *k*.

**sentence-transformers (`all-MiniLM-L6-v2`)** — fast, lightweight, and produces strong semantic embeddings for short survey responses without requiring an API call per fragment.

**LLM Semantic pipeline** — cosine similarity works well once you have many labelled examples, but for small or domain-specific datasets, reading the actual text is more reliable and produces more coherent cluster names. The streaming NDJSON approach gives researchers live feedback on a long-running process rather than a blank wait screen.

**Sanity Check** — qualitative coding is subjective and researchers sometimes make inconsistent placements, especially in long sessions. Surfacing a visual suggestion keeps the researcher in control while flagging obvious inconsistencies. The check is deliberately conservative: it only fires once the canvas has enough structure (at least one other group with 2+ members) and only flags when Claude is confident the placement is clearly wrong, not merely debatable.

---

## Setup

### Prerequisites

- Node.js 18+
- Python 3.11
- MongoDB Atlas account (free tier is fine) or a local MongoDB instance
- An Anthropic API key (or OpenAI / Ollama — see `.env` below)

### 1. Clone the repo

```bash
git clone https://github.com/nabilshanteer/thematic_clusters.git
cd thematic_clusters/NIE-prototype
```

### 2. Install Node dependencies

```bash
cd react-client && npm install && cd ..
cd api-server && npm install && cd ..
```

### 3. Set up the Python environment

```bash
cd ai-service
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r ../requirements.txt
python -m spacy download en_core_web_sm
cd ..
```

### 4. Configure environment variables

Create a `.env` file in `NIE-prototype/` (the root of this repo, one level above each service folder):

```env
# MongoDB
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/
MONGO_DB_NAME=nie

# LLM backend — choose one: anthropic | openai | ollama
LLM_BACKEND=anthropic

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# OpenAI (if LLM_BACKEND=openai)
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# Ollama (if LLM_BACKEND=ollama)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3
```

Create a `.env.local` file inside `react-client/`:

```env
VITE_API_URI=http://localhost:3000
VITE_AI_URI=http://localhost:8000
```

### 5. Run

From `react-client/`:

```bash
npm run dev:all
```

This starts all three services concurrently. Open **http://localhost:5173**.

To start services individually:

```bash
npm run dev   # React frontend only
npm run api   # Node.js API only
npm run ai    # Python AI service only
```

---

## Usage

1. Go to **Survey Ingestion** in the sidebar
2. Upload `demo_nhs_survey_v2.csv` (included) or your own CSV/XLSX
3. Enter a survey name and choose a pipeline
4. For **LLM Semantic** or **LLM Manual**, optionally enter a research question and column filters
5. Click **Run Pipeline** and watch progress
6. Click **View Cluster Graph** to explore the results

The included demo file has 30 synthetic NHS inpatient survey responses across 5 questions covering themes like discharge planning, pain management, staff communication, and infection control.

---

## Repository structure

```
NIE-prototype/
├── ai-service/               # Python FastAPI — all ML and LLM logic
│   ├── routers/              # One file per API route group
│   ├── services/             # Reusable service modules
│   ├── main.py               # App entry point, router registration
│   └── venv/                 # Python virtual environment (not in git)
├── api-server/               # Node.js Express — MongoDB CRUD
│   ├── drivers/              # MongoDB connection
│   ├── repositories/         # Collection-level query functions
│   └── index.ts              # Route definitions
├── react-client/             # React 18 + Vite frontend
│   ├── src/
│   │   ├── api/              # Facade modules wrapping each backend
│   │   ├── views/            # One file per page/view
│   │   ├── components/       # Shared UI components
│   │   ├── model/            # Data model types
│   │   └── state.js          # Jotai global state atoms
│   └── package.json
├── demo_nhs_survey_v2.csv    # Sample data for testing
└── requirements.txt          # Python dependencies
```

### `ai-service/routers/`

| File | Endpoint prefix | Purpose |
|---|---|---|
| `ingest.py` | `/ingest` | Parses CSV/XLSX, runs spaCy PII redaction, writes fragments to MongoDB |
| `embed.py` | `/embed` | Runs `all-MiniLM-L6-v2` on all fragments for a document |
| `cluster.py` | `/cluster` | UMAP (10D) → HDBSCAN → UMAP (2D) Auto clustering |
| `label.py` | `/label` | LLM labelling of clusters |
| `feedback.py` | `/feedback` | Records manual re-coding events and suggests placements |
| `suggest.py` | `/suggest` | Cosine similarity and LLM placement suggestions; sanity check |
| `llm_cluster.py` | `/llm-cluster` | Streaming LLM Semantic pipeline |

### `ai-service/services/`

| File | Purpose |
|---|---|
| `embedder.py` | sentence-transformers wrapper |
| `clusterer.py` | UMAP + HDBSCAN logic |
| `labeller.py` | LLM cluster label and summary generation |
| `llm_clusterer.py` | LLM call dispatch (Anthropic / OpenAI / Ollama), relevance filtering, iterative fragment assignment |
| `ner_redactor.py` | spaCy-based PII redaction — removes PERSON and DATE entities |
| `html_builder.py` | Converts raw row data into an HTML fragment representation |
| `mongo_client.py` | Shared MongoDB connection singleton |

### `react-client/src/views/`

| File | Purpose |
|---|---|
| `SurveyIngestionView.jsx` | Upload form, pipeline selector, live LLM log, column filters |
| `ManualPlacementView.jsx` | React Flow canvas — drag-and-drop grouping, sanity check arrows, placement suggestions |
| `ClusterGraphView.jsx` | Sigma.js force-directed graph of clusters and fragment nodes |
| `DocumentViewer.jsx` | Reads and displays stored document fragments |
| `WorkspaceArea.jsx` | Main workspace shell |
| `VirtualFloor.jsx` | Floor-based fragment browser and annotation canvas |

### `react-client/src/api/`

| File | Purpose |
|---|---|
| `aiServiceFacade.ts` | All calls to the Python AI service (port 8000) |
| `dataFacade.ts` | All calls to the Node.js API server (port 3000) |

---

## MongoDB collections

| Collection | Contents |
|---|---|
| `survey_docs` | One document per uploaded file — name, column list, timestamps |
| `fragments` | One per survey cell — raw text, redacted text, embedding vector, cluster assignment, full row data |
| `clusters` | One per discovered cluster — label, summary, colour, centroid, fragment ID list |
| `clusterFeedback` | Log of manual re-coding events (fragment moved from cluster A to cluster B) |

---

## Notes

- On **Windows**, uvicorn's `--reload` watcher sometimes serves stale routes when new Python files are added. If an endpoint isn't appearing, kill all Python processes on port 8000 and restart via `npm run dev:all`.
- The `.env` file must sit at `NIE-prototype/` root. The Python service searches up the directory tree with `find_dotenv()`, and the Node API server loads `../.env` relative to `api-server/`.
- `node_modules/` and `venv/` are excluded from version control. Run `npm install` and `pip install` after cloning.
