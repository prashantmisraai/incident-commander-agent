from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="Autonomous Incident Commander",
    description=(
        "**Bayer AI Hackathon 2026 — Agentic AI Track**\n\n"
        "A multi-agent AI system that autonomously detects, investigates, decides, and resolves "
        "cloud infrastructure incidents in real-time.\n\n"
        "**Agents:**\n"
        "- **Commander** — orchestrates the investigation plan\n"
        "- **Log Agent** — forensic log analysis\n"
        "- **Metrics Agent** — telemetry anomaly detection\n"
        "- **Deploy Agent** — CI/CD correlation\n"
        "- **Reasoning Engine** — cross-correlated root cause analysis\n"
        "- **Decision Engine** — auto-resolve vs. human escalation\n\n"
        "Powered by **LangGraph** + **Ollama (llama3.2)**"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Autonomous Incident Commander",
        "version": "1.0.0",
        "hackathon": "Bayer AI Hackathon 2026 — Agentic AI Track",
        "docs": "/docs",
        "health": "/api/v1/health",
        "demo": "POST /api/v1/demo/trigger",
        "ingest": "POST /api/v1/incidents/ingest",
        "list": "GET /api/v1/incidents",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
