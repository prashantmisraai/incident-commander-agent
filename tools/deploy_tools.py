import json
import os
from langchain_core.tools import tool

_MOCK_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mock_data")


def _load_deployments() -> dict:
    with open(os.path.join(_MOCK_DATA_DIR, "deployments.json")) as f:
        return json.load(f)


@tool
def get_recent_deployments(service: str, hours_back: int = 24) -> str:
    """Get recent CI/CD deployments for a service within the specified look-back window."""
    data = _load_deployments()
    deployments = [d for d in data["deployments"] if d["service"] == service]
    return json.dumps({
        "service": service,
        "recent_deployments": deployments,
        "deploy_count": len(deployments)
    }, indent=2)


@tool
def get_deployment_config_changes(service: str) -> str:
    """Get configuration keys that were modified during recent deployments for a service."""
    data = _load_deployments()
    config_changes = [c for c in data.get("config_changes", []) if c["service"] == service]
    return json.dumps({
        "service": service,
        "config_changes": config_changes,
        "high_risk_changes": [c for c in config_changes if c.get("severity") == "HIGH"]
    }, indent=2)


@tool
def get_incident_history(service: str) -> str:
    """Retrieve historical incidents for a service to identify repeated failure patterns."""
    data = _load_deployments()
    incidents = [i for i in data.get("incidents", []) if i["service"] == service]
    return json.dumps({
        "service": service,
        "historical_incidents": incidents,
        "incident_count": len(incidents)
    }, indent=2)


@tool
def get_rollback_options(service: str) -> str:
    """Determine available stable rollback targets for a service."""
    data = _load_deployments()
    deployments = [d for d in data["deployments"] if d["service"] == service]
    latest = deployments[-1] if deployments else None
    if not latest:
        return json.dumps({"error": f"No deployments found for {service}"})
    return json.dumps({
        "service": service,
        "current_version": latest["version"],
        "rollback_to": latest["rollback_version"],
        "rollback_available": True,
        "deployment_id": latest["id"]
    }, indent=2)
