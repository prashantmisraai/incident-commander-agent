from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from agents.commander import commander_node
from agents.log_agent import log_agent_node
from agents.metrics_agent import metrics_agent_node
from agents.deploy_agent import deploy_agent_node
from agents.reasoning_engine import (
    reasoning_node,
    decide_node,
    auto_resolve_node,
    human_notify_node,
    generate_report_node,
)


# ─── Shared State ──────────────────────────────────────────────────────────────

class IncidentState(TypedDict):
    incident_id: str
    alert: dict
    investigation_plan: str
    log_findings: Optional[dict]
    metrics_findings: Optional[dict]
    deploy_findings: Optional[dict]
    reasoning_summary: str
    decision: str          # "auto_resolve" | "human_in_loop"
    action_taken: str      # JSON-encoded action descriptor
    report: dict
    email_sent: bool


# ─── Conditional Router ────────────────────────────────────────────────────────

def _route_after_decision(state: IncidentState) -> str:
    """Route to auto_resolve or human_notify based on the Decision Engine output."""
    return state.get("decision", "human_in_loop")


# ─── Graph Builder ─────────────────────────────────────────────────────────────

def build_incident_graph():
    """
    Build and compile the LangGraph StateGraph.

    Flow:
        commander
            ├──► log_agent    ──┐
            ├──► metrics_agent ─┼──► reasoning ──► decide ──► auto_resolve   ──► generate_report ──► END
            └──► deploy_agent ──┘                        └──► human_notify ──┘
    """
    workflow = StateGraph(IncidentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    workflow.add_node("commander", commander_node)
    workflow.add_node("log_agent", log_agent_node)
    workflow.add_node("metrics_agent", metrics_agent_node)
    workflow.add_node("deploy_agent", deploy_agent_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("decide", decide_node)
    workflow.add_node("auto_resolve", auto_resolve_node)
    workflow.add_node("human_notify", human_notify_node)
    workflow.add_node("generate_report", generate_report_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    workflow.set_entry_point("commander")

    # ── Fan-out: commander dispatches all three specialists in parallel ─────────
    workflow.add_edge("commander", "log_agent")
    workflow.add_edge("commander", "metrics_agent")
    workflow.add_edge("commander", "deploy_agent")

    # ── Fan-in: reasoning waits for all three specialists to finish ────────────
    workflow.add_edge("log_agent", "reasoning")
    workflow.add_edge("metrics_agent", "reasoning")
    workflow.add_edge("deploy_agent", "reasoning")

    # ── Linear path: reasoning → decide ───────────────────────────────────────
    workflow.add_edge("reasoning", "decide")

    # ── Conditional split: auto-resolve vs. human escalation ──────────────────
    workflow.add_conditional_edges(
        "decide",
        _route_after_decision,
        {
            "auto_resolve": "auto_resolve",
            "human_in_loop": "human_notify",
        },
    )

    # ── Both paths converge at the report node ─────────────────────────────────
    workflow.add_edge("auto_resolve", "generate_report")
    workflow.add_edge("human_notify", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# ─── Singleton ─────────────────────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_incident_graph()
    return _graph
