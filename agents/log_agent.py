import json
from tools.log_tools import get_error_logs, get_stack_traces, get_error_timeline
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DEMO_MODE


def _get_llm():
    if DEMO_MODE:
        return None
    from langchain_ollama import ChatOllama
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)


_DEMO_ANALYSIS = (
    "[Log Agent — DEMO MODE]\n"
    "PRIMARY ERROR: java.lang.NullPointerException\n"
    "  at com.bayer.payment.PaymentProcessor.processCard(PaymentProcessor.java:142)\n"
    "  at com.bayer.payment.OrderService.checkout(OrderService.java:89)\n\n"
    "ERROR CASCADE:\n"
    "  NPE → DB connection pool exhaustion (timeout 5000ms) → circuit breaker OPEN\n"
    "  → retry limit exceeded (max=3) → HTTP 500 on /api/v1/checkout\n\n"
    "FIRST OCCURRENCE: 2026-03-25T14:32:01Z\n"
    "ERROR PATTERN: Sudden burst — all errors began within the same second\n\n"
    "IMPACTED COMPONENTS:\n"
    "  - payment-service (primary)\n"
    "  - payment-gateway (circuit breaker OPEN)\n\n"
    "LOG CONFIDENCE: HIGH — stack traces are consistent and unambiguous"
)


def log_agent_node(state: dict) -> dict:
    """
    Log Agent — The Forensic Expert.
    Deep-scans distributed application logs to find specific stack traces
    and error correlations.
    """
    service = state["alert"].get("service", "unknown")
    plan = state.get("investigation_plan", "")

    # ── Gather raw log data via tools ─────────────────────────────────────────
    raw_errors = get_error_logs.invoke({"service": service})
    raw_traces = get_stack_traces.invoke({"service": service})
    raw_timeline = get_error_timeline.invoke({"service": service})

    if DEMO_MODE:
        analysis = _DEMO_ANALYSIS
        print(f"[Log Agent] DEMO MODE — analysis ready ({len(analysis)} chars)")
        return {
            "log_findings": {
                "analysis": analysis,
                "raw_error_logs": json.loads(raw_errors),
                "raw_stack_traces": json.loads(raw_traces),
                "raw_timeline": json.loads(raw_timeline)
            }
        }

    llm = _get_llm()
    prompt = f"""You are the Log Agent — a Forensic Expert specialising in distributed systems log analysis.

Commander's Investigation Plan:
{plan}

── RAW LOG DATA ──────────────────────────────────────────────────────────────

ERROR LOGS:
{raw_errors}

STACK TRACES:
{raw_traces}

ERROR TIMELINE:
{raw_timeline}

── YOUR TASK ─────────────────────────────────────────────────────────────────
Analyse the log data above and report:

1. PRIMARY ERROR — What is the root exception / error? (class, method, line)
2. ERROR CASCADE — How did the first error trigger subsequent failures?
3. FIRST OCCURRENCE — Exact timestamp when errors began
4. ERROR PATTERN — Sudden burst vs. gradual escalation?
5. IMPACTED COMPONENTS — List every service/component affected
6. LOG CONFIDENCE — high / medium / low, with brief rationale

Be precise, reference actual log lines."""

    try:
        response = llm.invoke(prompt)
        analysis = response.content
    except Exception as exc:
        analysis = _DEMO_ANALYSIS + f"\n\n[Ollama error: {exc}]"

    print(f"[Log Agent] Analysis complete ({len(analysis)} chars)")
    return {
        "log_findings": {
            "analysis": analysis,
            "raw_error_logs": json.loads(raw_errors),
            "raw_stack_traces": json.loads(raw_traces),
            "raw_timeline": json.loads(raw_timeline)
        }
    }
