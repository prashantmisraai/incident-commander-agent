import json
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DEMO_MODE


def _get_llm():
    if DEMO_MODE:
        return None
    from langchain_ollama import ChatOllama
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)


def _demo_plan(alert: dict) -> str:
    service = alert.get('service', 'unknown-service')
    return (
        f"[Commander — DEMO MODE]\n"
        f"Investigation plan for alert on '{service}':\n\n"
        "1. ALERT ASSESSMENT\n"
        f"   Severity: {alert.get('severity', 'unknown').upper()} | Service: {service}\n"
        "   Blast radius: all checkout-path users (~850 req/min affected).\n"
        "   Initial hypothesis: recent deployment config change caused resource exhaustion.\n\n"
        "2. LOG AGENT DIRECTIVES\n"
        "   - Find NullPointerExceptions and stack traces in the last 30 minutes.\n"
        "   - Look for connection pool timeout messages (5000ms threshold).\n"
        "   - Identify circuit breaker OPEN events and retry exhaustion warnings.\n\n"
        "3. METRICS AGENT DIRECTIVES\n"
        "   - CPU threshold: flag anything above 80%.\n"
        "   - p99 latency threshold: flag anything above 1000ms.\n"
        "   - Error rate threshold: flag anything above 5%.\n"
        "   - Memory: detect unbounded growth (leak pattern).\n\n"
        "4. DEPLOY AGENT DIRECTIVES\n"
        "   - Check all deployments in the past 2 hours.\n"
        "   - Correlate config changes — specifically DB_POOL_MAX_CONNECTIONS.\n"
        "   - Review historical incidents for same failure pattern.\n\n"
        "5. TOP 3 HYPOTHESES\n"
        "   H1 (likely): Recent deployment reduced DB connection pool → exhaustion cascade.\n"
        "   H2: New async queue config introduced a deadlock under load.\n"
        "   H3: Upstream payment-gateway API change broke the integration."
    )


def commander_node(state: dict) -> dict:
    """
    Commander Agent — The Orchestrator.
    Evaluates the incoming alert and produces a structured investigation plan
    that guides the three specialist agents.
    """
    alert = state["alert"]

    if DEMO_MODE:
        plan = _demo_plan(alert)
        print(f"\n[Commander] DEMO MODE — plan generated ({len(plan)} chars)")
        return {"investigation_plan": plan}

    llm = _get_llm()
    system_msg = (
        "You are the Commander Agent — the Chief Orchestrator of an Autonomous Incident Response System "
        "for a high-velocity cloud environment.\n\n"
        "You coordinate three specialist agents:\n"
        "  • Log Agent       — forensic expert, scans distributed logs for stack traces and error chains\n"
        "  • Metrics Agent   — telemetry analyst, monitors CPU, p99 latency, memory leak patterns\n"
        "  • Deploy Agent    — historian, maps real-time errors against CI/CD deployments and config changes\n\n"
        "Your job: evaluate the alert, assess severity and blast radius, then write a precise, actionable "
        "investigation plan for each specialist agent."
    )

    user_msg = f"""An alert has just fired in production. Create a detailed investigation plan.

ALERT:
{json.dumps(alert, indent=2)}

Structure your response as:
1. ALERT ASSESSMENT — severity, affected systems, potential blast radius, initial hypotheses
2. LOG AGENT DIRECTIVES — what specific errors, stack traces, and patterns to look for
3. METRICS AGENT DIRECTIVES — which metrics to analyse, anomaly thresholds to apply
4. DEPLOY AGENT DIRECTIVES — what deployment and config changes to correlate against
5. TOP 3 HYPOTHESES — ranked list of most likely root causes

Be specific and actionable. Time is critical."""

    try:
        response = llm.invoke([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ])
        plan = response.content
    except Exception as exc:
        plan = _demo_plan(alert) + f"\n\n[Ollama error: {exc}]"

    print(f"\n[Commander] Investigation plan created ({len(plan)} chars)")
    return {"investigation_plan": plan}
