import json
import re
from datetime import datetime, timezone
from tools.resolver_tools import rollback_deployment, restart_service
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DEMO_MODE


def _get_llm():
    if DEMO_MODE:
        return None
    from langchain_ollama import ChatOllama
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)


_DEMO_RCA = (
    "[Reasoning Engine — DEMO MODE]\n\n"
    "1. DEFINITIVE ROOT CAUSE\n"
    "   Deployment v2.3.1 (14:24 UTC) reduced DB_POOL_MAX_CONNECTIONS from 10 to 5,\n"
    "   causing connection pool exhaustion under normal production load.\n\n"
    "2. CAUSAL CHAIN\n"
    "   Step 1 — 14:24:00Z  v2.3.1 deployed. DB pool shrunk: 10 → 5 connections.\n"
    "   Step 2 — 14:32:01Z  Pool exhausted. PaymentProcessor.processCard() throws\n"
    "                        NullPointerException (PaymentProcessor.java:142).\n"
    "   Step 3 — 14:32:03Z  All 5 slots occupied. New requests time-out after 5000ms.\n"
    "   Step 4 — 14:32:10Z  Circuit breaker OPEN for payment-gateway.\n"
    "   Step 5 — 14:33:00Z  Error rate 94%. Unclosed connections leak memory (+145MB/min).\n"
    "   Step 6 — 14:34:00Z  Kubernetes liveness probe fails; pod marked unhealthy.\n\n"
    "3. TIMELINE CORRELATION\n"
    "   Deployment (14:24) → Metrics spike (14:32, +8 min) → Log errors (14:32:01)\n"
    "   8-minute warm-up delay matches DB pool gradual saturation under 142 rps load.\n"
    "   All three agents corroborate the same 8-minute window.\n\n"
    "4. BLAST RADIUS\n"
    "   100% of /api/v1/checkout requests failing. Throughput: 142 rps → 8 rps.\n"
    "   Estimated ~850 users/minute receiving HTTP 500 errors.\n\n"
    "5. CONFIDENCE LEVEL: HIGH\n"
    "   - Log Agent: NPE at exact DB connection call site (HIGH confidence)\n"
    "   - Metrics Agent: Simultaneous CPU+latency+error spike at 14:32 (HIGH)\n"
    "   - Deploy Agent: Config change DB_POOL 10→5 confirmed, historical precedent matches (HIGH)\n\n"
    "6. RECOMMENDED ACTION: Rollback to v2.3.0 immediately.\n\n"
    "7. URGENCY: CRITICAL — OOMKill imminent (memory 1,678MB / 2,048MB limit).\n"
    "   Act within the next 2 minutes to prevent pod restart loop."
)


# ─── Reasoning Node ────────────────────────────────────────────────────────────

def reasoning_node(state: dict) -> dict:
    """
    Reasoning Engine — The Master Correlator.
    Cross-correlates findings from all three specialist agents to produce
    a definitive root cause analysis and ranked action recommendation.
    """
    log_analysis = (state.get("log_findings") or {}).get("analysis", "No log findings available.")
    metrics_analysis = (state.get("metrics_findings") or {}).get("analysis", "No metrics findings available.")
    deploy_analysis = (state.get("deploy_findings") or {}).get("analysis", "No deploy findings available.")

    if DEMO_MODE:
        print(f"[Reasoning Engine] DEMO MODE — RCA ready ({len(_DEMO_RCA)} chars)")
        return {"reasoning_summary": _DEMO_RCA}

    llm = _get_llm()
    prompt = f"""You are the Reasoning Engine — the master intelligence layer of the Autonomous Incident Commander.

Three specialist agents have completed their investigations. Your job is to cross-correlate all evidence
and produce a definitive Root Cause Analysis.

══════════════════════════════════════════════════════════════════════════════
LOG AGENT FINDINGS
══════════════════════════════════════════════════════════════════════════════
{log_analysis}

══════════════════════════════════════════════════════════════════════════════
METRICS AGENT FINDINGS
══════════════════════════════════════════════════════════════════════════════
{metrics_analysis}

══════════════════════════════════════════════════════════════════════════════
DEPLOY INTELLIGENCE FINDINGS
══════════════════════════════════════════════════════════════════════════════
{deploy_analysis}

── YOUR TASK ─────────────────────────────────────────────────────────────────
Produce a structured Root Cause Analysis:

1. DEFINITIVE ROOT CAUSE (one sentence — the single most likely cause)
2. CAUSAL CHAIN (numbered, step-by-step sequence from trigger to failure)
3. TIMELINE CORRELATION (link deployment timestamp → metric anomaly → log errors)
4. BLAST RADIUS (which systems/users are affected and how severely)
5. CONFIDENCE LEVEL (high/medium/low with your reasoning)
6. RECOMMENDED ACTION (rollback to X / restart / config-fix / escalate to human)
7. URGENCY (critical — act now / high — act within 5 min / medium — monitor)

Use evidence from all three agents. Be definitive."""

    try:
        response = llm.invoke(prompt)
        reasoning = response.content
    except Exception as exc:
        reasoning = _DEMO_RCA + f"\n\n[Ollama error: {exc}]"

    print(f"[Reasoning Engine] RCA complete ({len(reasoning)} chars)")
    return {"reasoning_summary": reasoning}


# ─── Decision Node ─────────────────────────────────────────────────────────────

def decide_node(state: dict) -> dict:
    """
    Decision Engine.
    Evaluates the RCA and decides between auto-resolution and human escalation.
    Outputs a structured JSON decision that drives the conditional routing.
    """
    reasoning = state.get("reasoning_summary", "")

    if DEMO_MODE:
        # In demo mode, derive the decision deterministically from the RCA text
        text_lower = reasoning.lower()
        if "high" in text_lower and "rollback" in text_lower:
            decision_data = {
                "decision": "auto_resolve",
                "action_type": "rollback",
                "target_version": "v2.3.0",
                "service": state["alert"].get("service", "payment-service"),
                "confidence": 0.95,
                "reason": "DEMO MODE: High-confidence deployment failure. Rollback to last stable version.",
                "estimated_resolution_minutes": 5,
            }
        else:
            decision_data = {
                "decision": "human_in_loop",
                "action_type": "escalate",
                "target_version": None,
                "service": state["alert"].get("service", "payment-service"),
                "confidence": 0.50,
                "reason": "DEMO MODE: Insufficient confidence for automated resolution.",
                "estimated_resolution_minutes": 30,
            }
        print(f"[Decision Engine] DEMO MODE — decision: {decision_data['decision']} "
              f"(confidence: {decision_data['confidence']})")
        return {
            "decision": decision_data["decision"],
            "action_taken": json.dumps(decision_data)
        }

    llm = _get_llm()
    prompt = f"""You are the Decision Engine for an Autonomous Incident Commander system.

Based on the Root Cause Analysis below, decide the appropriate response.

ROOT CAUSE ANALYSIS:
{reasoning}

DECISION RULES:
- Use "auto_resolve" when confidence is HIGH and the action is a safe rollback or restart
- Use "human_in_loop" when confidence is LOW/MEDIUM, or the situation requires human judgement
- Auto-resolve is preferred when a prior stable version is available

Respond with ONLY a valid JSON object — no markdown, no extra text:

{{
  "decision": "auto_resolve",
  "action_type": "rollback",
  "target_version": "v2.3.0",
  "service": "payment-service",
  "confidence": 0.95,
  "reason": "High-confidence deployment-caused failure with a known stable rollback target.",
  "estimated_resolution_minutes": 5
}}"""

    decision_data = None
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            decision_data = json.loads(json_match.group())
    except Exception:
        pass

    if not decision_data:
        # Heuristic fallback: look for strong signals in the reasoning text
        text_lower = reasoning.lower()
        if (
            "high" in text_lower
            and ("rollback" in text_lower or "restart" in text_lower)
            and "critical" in text_lower
        ):
            decision_data = {
                "decision": "auto_resolve",
                "action_type": "rollback",
                "target_version": "v2.3.0",
                "service": state["alert"].get("service", "payment-service"),
                "confidence": 0.92,
                "reason": "Heuristic: high-confidence deployment failure with rollback available.",
                "estimated_resolution_minutes": 5,
            }
        else:
            decision_data = {
                "decision": "human_in_loop",
                "action_type": "escalate",
                "target_version": None,
                "service": state["alert"].get("service", "payment-service"),
                "confidence": 0.50,
                "reason": "Insufficient confidence for automated resolution.",
                "estimated_resolution_minutes": 30,
            }

    print(f"[Decision Engine] Decision: {decision_data.get('decision')} "
          f"(confidence: {decision_data.get('confidence')})")
    return {
        "decision": decision_data.get("decision", "human_in_loop"),
        "action_taken": json.dumps(decision_data)
    }


# ─── Auto Resolver Node ────────────────────────────────────────────────────────

def auto_resolve_node(state: dict) -> dict:
    """
    Auto Resolver — executes the chosen remediation action (rollback / restart).
    """
    try:
        action_data = json.loads(state.get("action_taken", "{}"))
    except Exception:
        action_data = {}

    service = action_data.get("service", state["alert"].get("service", "payment-service"))
    action_type = action_data.get("action_type", "rollback")
    target_version = action_data.get("target_version")

    if action_type == "rollback" and target_version:
        raw = rollback_deployment.invoke({"service": service, "target_version": target_version})
    else:
        raw = restart_service.invoke({"service": service})

    exec_result = json.loads(raw)
    print(f"[Auto Resolver] Action executed: {exec_result.get('action')} → {exec_result.get('status')}")
    return {"action_taken": json.dumps({**action_data, "execution_result": exec_result})}


# ─── Human Notify Node ─────────────────────────────────────────────────────────

def human_notify_node(state: dict) -> dict:
    """
    Human-in-Loop Node — flags that the incident requires manual intervention.
    The actual email is sent in generate_report_node after the full report is assembled.
    """
    try:
        action_data = json.loads(state.get("action_taken", "{}"))
    except Exception:
        action_data = {}

    updated = {**action_data, "human_notified": True, "notification_type": "email"}
    print("[Human Notify] Escalation flagged — email will be sent with full report.")
    return {"action_taken": json.dumps(updated)}


# ─── Report Node ───────────────────────────────────────────────────────────────

def generate_report_node(state: dict) -> dict:
    """
    Reporting Node — assembles the final incident report and triggers email notification.
    """
    from notifications.email_notifier import send_incident_email  # avoid circular at module level

    alert = state["alert"]
    decision = state.get("decision", "unknown")
    try:
        action_data = json.loads(state.get("action_taken", "{}"))
    except Exception:
        action_data = {}

    exec_result = action_data.get("execution_result", {})
    resolution_msg = (
        exec_result.get("message", "Action executed")
        if decision == "auto_resolve"
        else "Incident escalated to on-call team for manual investigation."
    )

    report = {
        "incident_id": state.get("incident_id", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alert": alert,
        "status": "resolved" if decision == "auto_resolve" else "escalated",
        "severity": alert.get("severity", "unknown"),
        "affected_service": alert.get("service"),
        "root_cause_analysis": state.get("reasoning_summary", ""),
        "decision": decision,
        "action_taken": action_data,
        "resolution": resolution_msg,
        "next_steps": (
            [
                "Monitor service metrics for 15 minutes post-rollback.",
                f"Verify {action_data.get('service')} health checks are passing.",
                "Open post-mortem ticket for v2.3.1 root cause fix.",
                "Update DB_POOL_MAX_CONNECTIONS to minimum of 10 before re-deploying."
            ]
            if decision == "auto_resolve"
            else [
                "On-call engineer: review the Root Cause Analysis section.",
                "Determine if rollback to v2.3.0 is appropriate.",
                "Check DB_POOL_MAX_CONNECTIONS config change in v2.3.1.",
                "Update runbook with findings after resolution."
            ]
        )
    }

    email_sent = False
    try:
        email_sent = send_incident_email(state, report)
    except Exception as exc:
        print(f"[Report] Email notification failed: {exc}")

    print(f"[Report] Incident report generated. Email sent: {email_sent}")
    return {"report": report, "email_sent": email_sent}
