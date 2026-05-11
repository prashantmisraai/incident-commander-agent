import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM ──────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# When DEMO_MODE=true the agents skip Ollama entirely and return pre-built
# deterministic analysis responses.  Use this when Ollama is not installed.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ─── Email ────────────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "oncall@company.com")
MOCK_EMAIL = os.getenv("MOCK_EMAIL", "true").lower() == "true"

# ─── Paths ────────────────────────────────────────────────────────────────────
MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")
