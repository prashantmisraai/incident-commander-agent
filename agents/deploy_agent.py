import json
from tools.deploy_tools import (
    get_recent_deployments,
    get_deployment_config_changes,
    get_incident_history,
    get_rollback_options,
)
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DEMO_MODE


def _get_llm():
    if DEMO_MODE:
        return None
    from langchain_ollama import ChatOllama
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)


_DEMO_ANALYSIS = (
    "[Deploy Agent — DEMO MODE]\n"
    "DEPLOYMENT TIMELINE:\n"
    "  14:24:00Z — v2.3.1 deployed to production (8 minutes before alert)\n"
    "  14:20:00Z — v2.3.0 was the previous stable version\n\n"
    "SUSPICIOUS CHANGES:\n"
    "  DB_POOL_MAX_CONNECTIONS: 10 → 5  [SEVERITY: HIGH]\n"
    "  Halving the connection pool under the same request load (142 rps)\n"
    "  guarantees exhaustion. Each request holds a connection for ~35ms,\n"
    "  meaning 5 slots can only service 142 req/s at 100% pool occupancy.\n\n"
    "DEPLOYMENT CORRELATION: CONFIRMED\n"
    "  Gap: 8 minutes between v2.3.1 deploy (14:24Z) and failure onset (14:32Z).\n"
    "  8-minute delay matches DB pool warm-up exhaustion under sustained load.\n\n"
    "HISTORICAL PATTERN: MATCH\n"
    "  INC-2026-03-10-001: Identical connection pool exhaustion after\n"
    "  DB_POOL_MAX_CONNECTIONS was set to 3. Resolved by rollback + config fix.\n"
    "  Time-to-detect: 8 min. Time-to-resolve: 15 min.\n\n"
    "ROLLBACK RECOMMENDATION: YES — rollback to v2.3.0\n"
    "  Risk: LOW. v2.3.0 is the immediately preceding stable version.\n"
    "  Historical incident proves this pattern resolves via rollback.\n\n"
    "ROOT CAUSE HYPOTHESIS:\n"
    "  v2.3.1 config change (DB_POOL_MAX_CONNECTIONS: 10→5) caused connection\n"
    "  pool exhaustion which triggered the NullPointerException cascade."
)


def deploy_agent_node(state: dict) -> dict:
    """
    Deploy Intelligence Agent — The Historian.
    Maps real-time errors against the timeline of CI/CD deployments
    and service configuration changes to surface causal links.
    """
    service = state["alert"].get("service", "unknown")
    plan = state.get("investigation_plan", "")
    alert_time = state["alert"].get("timestamp", "")

    # ── Gather deployment data via tools ──────────────────────────────────────
    raw_deployments = get_recent_deployments.invoke({"service": service})
    raw_config = get_deployment_config_changes.invoke({"service": service})
    raw_history = get_incident_history.invoke({"service": service})
    raw_rollback = get_rollback_options.invoke({"service": service})

    if DEMO_MODE:
        analysis = _DEMO_ANALYSIS
        print(f"[Deploy Agent] DEMO MODE — analysis ready ({len(analysis)} chars)")
        return {
            "deploy_findings": {
                "analysis": analysis,
                "raw_deployments": json.loads(raw_deployments),
                "raw_config_changes": json.loads(raw_config),
                "raw_history": json.loads(raw_history),
                "raw_rollback": json.loads(raw_rollback)
            }
        }

    llm = _get_llm()
    prompt = f"""You are the Deploy Intelligence Agent — The Historian who maps production incidents
to CI/CD deployment events and configuration changes.

Commander's Investigation Plan:
{plan}

Alert fired at: {alert_time}

── DEPLOYMENT DATA ───────────────────────────────────────────────────────────

RECENT DEPLOYMENTS:
{raw_deployments}

CONFIGURATION CHANGES:
{raw_config}

HISTORICAL INCIDENTS:
{raw_history}

ROLLBACK OPTIONS:
{raw_rollback}

── YOUR TASK ─────────────────────────────────────────────────────────────────
Analyse the deployment data and report:

1. DEPLOYMENT TIMELINE — List all deployments and their exact timestamps relative to the alert
2. SUSPICIOUS CHANGES — Which config changes are high-risk? Why?
3. DEPLOYMENT CORRELATION — Is there a direct temporal link between a deployment and the incident?
   Calculate the gap in minutes between the latest deployment and alert time.
4. HISTORICAL PATTERN — Has this service had similar incidents after similar changes before?
5. ROLLBACK RECOMMENDATION — Should we rollback? To which version? Any risks?
6. ROOT CAUSE HYPOTHESIS — Based purely on deployment/config evidence

Use exact timestamps and config key names."""

    try:
        response = llm.invoke(prompt)
        analysis = response.content
    except Exception as exc:
        analysis = _DEMO_ANALYSIS + f"\n\n[Ollama error: {exc}]"

    print(f"[Deploy Agent] Analysis complete ({len(analysis)} chars)")
    return {
        "deploy_findings": {
            "analysis": analysis,
            "raw_deployments": json.loads(raw_deployments),
            "raw_config_changes": json.loads(raw_config),
            "raw_history": json.loads(raw_history),
            "raw_rollback": json.loads(raw_rollback)
        }
    }
