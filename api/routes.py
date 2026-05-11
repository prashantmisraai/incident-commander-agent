import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from schemas.models import AlertPayload, AlertSeverity, IncidentStatus
from graph.incident_graph import get_graph

router = APIRouter(prefix="/api/v1", tags=["Incidents"])

# ─── In-memory store (replace with Redis/DB for production) ───────────────────
incident_store: dict[str, dict] = {}


# ─── Background worker ─────────────────────────────────────────────────────────

def _run_workflow(incident_id: str, alert: dict) -> None:
    """Invoke the LangGraph workflow synchronously in a background thread."""
    try:
        graph = get_graph()
        initial_state = {
            "incident_id": incident_id,
            "alert": alert,
            "investigation_plan": "",
            "log_findings": None,
            "metrics_findings": None,
            "deploy_findings": None,
            "reasoning_summary": "",
            "decision": "",
            "action_taken": "",
            "report": {},
            "email_sent": False,
        }
        result = graph.invoke(initial_state)
        incident_store[incident_id].update({
            "status": IncidentStatus.COMPLETED,
            **result,
        })
        print(f"[Workflow] Incident {incident_id} completed — decision: {result.get('decision')}")
    except Exception as exc:
        incident_store[incident_id].update({
            "status": IncidentStatus.FAILED,
            "error": str(exc),
        })
        print(f"[Workflow] Incident {incident_id} FAILED: {exc}")


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.post("/incidents/ingest", summary="Submit an alert for autonomous investigation")
async def ingest_alert(alert: AlertPayload, background_tasks: BackgroundTasks):
    """
    Accepts a JSON alert payload and kicks off the multi-agent investigation pipeline.
    Returns an `incident_id` that can be polled for results.
    """
    incident_id = str(uuid.uuid4())
    incident_store[incident_id] = {
        "incident_id": incident_id,
        "status": IncidentStatus.PROCESSING,
        "alert": alert.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    background_tasks.add_task(_run_workflow, incident_id, alert.model_dump())
    return {
        "incident_id": incident_id,
        "status": "processing",
        "message": "Alert received. Autonomous investigation pipeline started.",
        "poll_url": f"/api/v1/incidents/{incident_id}",
    }


@router.get("/incidents/{incident_id}", summary="Get incident status and full report")
async def get_incident(incident_id: str):
    """Poll this endpoint to check progress and retrieve the final report."""
    if incident_id not in incident_store:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return incident_store[incident_id]


@router.get("/incidents", summary="List all incidents")
async def list_incidents():
    """Returns a summary list of all incidents processed in this session."""
    return {
        "total": len(incident_store),
        "incidents": [
            {
                "incident_id": v["incident_id"],
                "status": v.get("status"),
                "service": (v.get("alert") or {}).get("service"),
                "severity": (v.get("alert") or {}).get("severity"),
                "decision": v.get("decision"),
                "created_at": v.get("created_at"),
            }
            for v in incident_store.values()
        ],
    }


@router.post("/demo/trigger", summary="Trigger the built-in payment-service demo scenario")
async def trigger_demo(background_tasks: BackgroundTasks):
    """
    Fires the pre-built Bayer Hackathon 2026 scenario:
    payment-service v2.3.1 deployment at 14:24 UTC → cascading failures at 14:32 UTC.
    """
    demo_alert = AlertPayload(
        alert_id=f"alert-demo-{str(uuid.uuid4())[:8]}",
        service="payment-service",
        severity=AlertSeverity.CRITICAL,
        timestamp="2026-03-25T14:32:00Z",
        description=(
            "High error rate detected: 94% of requests returning HTTP 500. "
            "CPU at 95%. p99 latency 12,000ms. Service health check failing."
        ),
        metadata={
            "affected_pods": ["pod-payment-7d9f8b-xkz9p", "pod-payment-7d9f8b-abc12"],
            "error_type": "NullPointerException",
            "error_rate_percent": 94.3,
            "cpu_percent": 95,
            "p99_latency_ms": 12000,
            "alerting_system": "prometheus",
            "namespace": "production",
            "cluster": "bayer-prod-eks",
        },
    )

    incident_id = str(uuid.uuid4())
    incident_store[incident_id] = {
        "incident_id": incident_id,
        "status": IncidentStatus.PROCESSING,
        "alert": demo_alert.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": True,
    }
    background_tasks.add_task(_run_workflow, incident_id, demo_alert.model_dump())
    return {
        "incident_id": incident_id,
        "status": "processing",
        "message": "Demo scenario triggered: payment-service v2.3.1 deployment incident.",
        "scenario": "CPU spike + NullPointerException cascade 8 min after deployment at 14:24 UTC.",
        "poll_url": f"/api/v1/incidents/{incident_id}",
    }


@router.get("/health", summary="Health check")
async def health_check():
    return {
        "status": "healthy",
        "service": "autonomous-incident-commander",
        "version": "1.0.0",
        "active_incidents": sum(
            1 for v in incident_store.values()
            if v.get("status") == IncidentStatus.PROCESSING
        ),
    }
