import json
import os
from langchain_core.tools import tool

_MOCK_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mock_data")


def _load_logs() -> dict:
    with open(os.path.join(_MOCK_DATA_DIR, "logs.json")) as f:
        return json.load(f)


@tool
def get_error_logs(service: str, time_window_minutes: int = 30) -> str:
    """Query application logs for ERROR and CRITICAL level entries within a time window."""
    data = _load_logs()
    errors = [
        log for log in data["logs"]
        if log["level"] in ("ERROR", "CRITICAL", "WARN")
    ]
    return json.dumps({
        "service": service,
        "error_logs": errors,
        "total_errors": len(errors)
    }, indent=2)


@tool
def get_stack_traces(service: str) -> str:
    """Extract stack traces from application logs to identify the failing code path."""
    data = _load_logs()
    traces = [log for log in data["logs"] if "stack_trace" in log]
    return json.dumps({"service": service, "stack_traces": traces}, indent=2)


@tool
def get_error_timeline(service: str) -> str:
    """Get a chronological timeline of errors to understand when failures started and how they escalated."""
    data = _load_logs()
    timeline = [
        {
            "timestamp": log["timestamp"],
            "level": log["level"],
            "message": log["message"]
        }
        for log in data["logs"] if log["level"] in ("ERROR", "CRITICAL")
    ]
    return json.dumps({"service": service, "error_timeline": timeline}, indent=2)
