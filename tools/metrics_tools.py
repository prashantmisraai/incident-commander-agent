import json
import os
from langchain_core.tools import tool

_MOCK_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mock_data")


def _load_metrics() -> dict:
    with open(os.path.join(_MOCK_DATA_DIR, "metrics.json")) as f:
        return json.load(f)


@tool
def get_cpu_metrics(service: str) -> str:
    """Get CPU utilization percentage over time for a service. Detects spikes above 80%."""
    data = _load_metrics()
    recent = data["cpu_percent"][-10:]
    max_cpu = max(d["value"] for d in recent)
    return json.dumps({
        "service": service,
        "cpu_metrics": recent,
        "max_cpu_percent": max_cpu,
        "anomaly_detected": max_cpu > 80,
        "baseline_cpu_percent": recent[0]["value"]
    }, indent=2)


@tool
def get_latency_metrics(service: str) -> str:
    """Get p99 latency in milliseconds over time. Detects latency above 1000ms (1 second)."""
    data = _load_metrics()
    recent = data["p99_latency_ms"][-10:]
    max_latency = max(d["value"] for d in recent)
    return json.dumps({
        "service": service,
        "p99_latency_ms": recent,
        "max_p99_latency_ms": max_latency,
        "anomaly_detected": max_latency > 1000,
        "baseline_latency_ms": recent[0]["value"]
    }, indent=2)


@tool
def get_error_rate(service: str) -> str:
    """Get request error rate as a percentage over time. Detects rates above 5%."""
    data = _load_metrics()
    recent = data["error_rate_percent"][-10:]
    current = recent[-1]["value"] if recent else 0
    return json.dumps({
        "service": service,
        "error_rate_history": recent,
        "current_error_rate_percent": current,
        "anomaly_detected": current > 5,
        "baseline_error_rate_percent": recent[0]["value"]
    }, indent=2)


@tool
def get_memory_metrics(service: str) -> str:
    """Get memory consumption in MB over time. Detects potential memory leaks."""
    data = _load_metrics()
    recent = data["memory_mb"][-10:]
    current = recent[-1]["value"] if recent else 0
    baseline = recent[0]["value"] if recent else 0
    growth = current - baseline
    return json.dumps({
        "service": service,
        "memory_mb": recent,
        "current_memory_mb": current,
        "baseline_memory_mb": baseline,
        "growth_mb": growth,
        "memory_leak_suspected": growth > 500
    }, indent=2)
