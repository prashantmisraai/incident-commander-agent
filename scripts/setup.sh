#!/usr/bin/env bash
# setup.sh — One-time setup: create venv, install deps, pull Ollama model, copy .env
# Run from the autonomous_incident_commander/ directory.

set -euo pipefail

echo "==========================================="
echo " Autonomous Incident Commander — Setup"
echo "==========================================="

# ── Python virtual environment ────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
fi

echo "[2/4] Installing Python dependencies..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

# ── .env file ─────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "[3/4] Creating .env from example..."
  cp .env.example .env
  echo "      ✏️  Edit .env to configure SMTP settings if needed."
else
  echo "[3/4] .env already exists — skipping."
fi

# ── Ollama model ──────────────────────────────────────────────────────────────
echo "[4/4] Pulling Ollama model (llama3.2)..."
if command -v ollama &> /dev/null; then
  ollama pull llama3.2
else
  echo "      ⚠️  Ollama not found in PATH."
  echo "      Install from https://ollama.com/download, then run: ollama pull llama3.2"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Start the server:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --reload"
echo ""
echo "Run the demo:"
echo "  python scripts/demo.py"
echo ""
echo "API docs:"
echo "  http://localhost:8000/docs"
