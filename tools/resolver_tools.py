import json
from datetime import datetime, timezone
from langchain_core.tools import tool


@tool
def rollback_deployment(service: str, target_version: str) -> str:
    """
    Execute a deployment rollback for a service to a specified stable version.
    In production this calls the Kubernetes/ECS rollout API.
    """
    result = {
        "status": "success",
        "action": "rollback",
        "service": service,
        "rolled_back_to": target_version,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Rollback of {service} to {target_version} initiated successfully.",
        "estimated_completion_seconds": 60,
        "mock": True
    }
    return json.dumps(result, indent=2)


@tool
def restart_service(service: str) -> str:
    """
    Perform a rolling restart of a service without changing its version.
    Useful for clearing transient state (memory leaks, hung threads).
    """
    result = {
        "status": "success",
        "action": "rolling_restart",
        "service": service,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Rolling restart of {service} initiated successfully.",
        "estimated_completion_seconds": 30,
        "mock": True
    }
    return json.dumps(result, indent=2)


@tool
def scale_service(service: str, replica_count: int) -> str:
    """
    Scale a service to the specified number of replicas.
    Use replica_count=0 to take a service offline immediately.
    """
    result = {
        "status": "success",
        "action": "scale",
        "service": service,
        "replica_count": replica_count,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
        "message": f"{service} scaled to {replica_count} replica(s).",
        "mock": True
    }
    return json.dumps(result, indent=2)
