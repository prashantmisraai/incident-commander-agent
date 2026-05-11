import json
from tools.metrics_tools import get_cpu_metrics, get_latency_metrics, get_error_rate, get_memory_metrics
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DEMO_MODE


def _get_llm():
    if DEMO_MODE:
        return None
    from langchain_ollama import ChatOllama
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)


_DEMO_ANALYSIS = (
    "[Metrics Agent — DEMO MODE]\n"
    "ANOMALY SUMMARY:\n"
    "  CPU         : 38% → 97%   (+155% spike at 14:32 UTC)\n"
    "  p99 Latency : 120ms → 12,000ms  (+9,900% — 100× baseline)\n"
    "  Error Rate  : 0.1% → 97.1%  (service effectively down)\n"
    "  Memory      : 512MB → 1,678MB  (+1,166MB in 8 minutes)\n\n"
    "ANOMALY ONSET: All metrics deviated simultaneously at 2026-03-25T14:32:00Z\n\n"
    "CORRELATION:\n"
    "  CPU spike and latency spike are simultaneous (DB wait → CPU spin).\n"
    "  Error rate followed 60 seconds later as retries exhausted.\n"
    "  Memory growing at ~145MB/min — OOMKill imminent (limit: 2,048MB).\n\n"
    "MEMORY LEAK ASSESSMENT: YES — linear unbounded growth consistent with\n"
    "  unclosed DB connections accumulating in the connection pool.\n\n"
    "PERFORMANCE IMPACT:\n"
    "  Throughput collapsed: 142 rps → 8 rps (94% drop).\n"
    "  ~850 users/minute receiving HTTP 500 on /api/v1/checkout.\n\n"
    "METRICS SIGNAL: Sudden correlated degradation 8 minutes after the\n"
    "  14:24 UTC deployment strongly implicates that deployment as the cause."
)


def metrics_agent_node(state: dict) -> dict:
    """
    Metrics Agent — The Telemetry Analyst.
    Monitors performance counters (CPU, p99 Latency, Memory Leak patterns)
    to spot and characterise anomalies.
    """
    service = state["alert"].get("service", "unknown")
    plan = state.get("investigation_plan", "")

    # ── Gather raw metrics via tools ──────────────────────────────────────────
    raw_cpu = get_cpu_metrics.invoke({"service": service})
    raw_latency = get_latency_metrics.invoke({"service": service})
    raw_error_rate = get_error_rate.invoke({"service": service})
    raw_memory = get_memory_metrics.invoke({"service": service})

    if DEMO_MODE:
        analysis = _DEMO_ANALYSIS
        print(f"[Metrics Agent] DEMO MODE — analysis ready ({len(analysis)} chars)")
        return {
            "metrics_findings": {
                "analysis": analysis,
                "raw_cpu": json.loads(raw_cpu),
                "raw_latency": json.loads(raw_latency),
                "raw_error_rate": json.loads(raw_error_rate),
                "raw_memory": json.loads(raw_memory)
            }
        }

    llm = _get_llm()
    prompt = f"""You are the Metrics Agent — a Telemetry Analyst for system performance monitoring.

Commander's Investigation Plan:
{plan}

── RAW METRICS DATA ──────────────────────────────────────────────────────────

CPU UTILISATION:
{raw_cpu}

P99 LATENCY (ms):
{raw_latency}

ERROR RATE (%):
{raw_error_rate}

MEMORY USAGE (MB):
{raw_memory}

── YOUR TASK ─────────────────────────────────────────────────────────────────
Analyse the metrics above and report:

1. ANOMALY SUMMARY — Which metrics are outside normal ranges and by how much?
2. ANOMALY ONSET — Exact timestamp when each metric first deviated
3. CORRELATION — Do multiple metrics degrade simultaneously? What's the order?
4. MEMORY LEAK ASSESSMENT — Is memory growing unboundedly? Rate of growth?
5. PERFORMANCE IMPACT — Quantify the degradation (e.g., latency increased 100×)
6. METRICS SIGNAL — What does this pattern suggest about the root cause?

Use specific numbers from the data."""

    try:
        response = llm.invoke(prompt)
        analysis = response.content
    except Exception as exc:
        analysis = _DEMO_ANALYSIS + f"\n\n[Ollama error: {exc}]"

    print(f"[Metrics Agent] Analysis complete ({len(analysis)} chars)")
    return {
        "metrics_findings": {
            "analysis": analysis,
            "raw_cpu": json.loads(raw_cpu),
            "raw_latency": json.loads(raw_latency),
            "raw_error_rate": json.loads(raw_error_rate),
            "raw_memory": json.loads(raw_memory)
        }
    }
