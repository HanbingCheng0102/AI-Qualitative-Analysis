from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv

# Search up the directory tree so the root-level .env is found
# when running from ai-service/ or any subdirectory
load_dotenv(find_dotenv())

from routers import ingest, embed, cluster, label, feedback, suggest, llm_cluster

app = FastAPI(title="NIE AI Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(embed.router, prefix="/embed", tags=["embed"])
app.include_router(cluster.router, prefix="/cluster", tags=["cluster"])
app.include_router(label.router, prefix="/label", tags=["label"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.include_router(suggest.router, prefix="/suggest", tags=["suggest"])
app.include_router(llm_cluster.router, prefix="/llm-cluster", tags=["llm-cluster"])


@app.get("/health")
def health():
    return {"status": "ok"}
