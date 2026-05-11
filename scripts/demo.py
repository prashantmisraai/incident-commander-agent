#!/usr/bin/env python3
"""
demo.py — Fire the demo incident scenario and stream live progress to the terminal.

Usage:
    python scripts/demo.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

DEFAULT_BASE = "http://localhost:8000"


def request(method: str, url: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def print_section(title: str, content: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")
    if content:
        print(content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    # ── 1. Health check ────────────────────────────────────────────────────
    print("\n🚀 Autonomous Incident Commander — Demo")
    print(f"   Target: {base}\n")
    try:
        health = request("GET", f"{base}/api/v1/health")
        print(f"✅ Server healthy: {health}")
    except Exception as exc:
        print(f"❌ Cannot reach server at {base}: {exc}")
        print("   Make sure the app is running:  uvicorn main:app --reload")
        sys.exit(1)

    # ── 2. Trigger demo scenario ───────────────────────────────────────────
    print("\n📡 Triggering demo scenario: payment-service incident...")
    result = request("POST", f"{base}/api/v1/demo/trigger")
    incident_id = result["incident_id"]
    print(f"   Incident ID : {incident_id}")
    print(f"   Scenario    : {result.get('scenario')}")
    print(f"   Poll URL    : {base}{result.get('poll_url')}")

    # ── 3. Poll until complete ─────────────────────────────────────────────
    print("\n⏳ Waiting for multi-agent investigation to complete...")
    print("   (This may take 30-120 seconds depending on Ollama response time)\n")

    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spin_i = 0
    start = time.time()

    while True:
        elapsed = int(time.time() - start)
        try:
            incident = request("GET", f"{base}/api/v1/incidents/{incident_id}")
        except Exception as exc:
            print(f"\n❌ Poll failed: {exc}")
            sys.exit(1)

        status = incident.get("status", "processing")
        spin_char = spinner[spin_i % len(spinner)]
        print(f"\r   {spin_char} Status: {status:<12} | Elapsed: {elapsed}s ", end="", flush=True)
        spin_i += 1

        if status in ("completed", "failed"):
            print()
            break

        if elapsed > 300:
            print("\n⚠️  Timed out after 5 minutes. Check server logs.")
            sys.exit(1)

        time.sleep(2)

    # ── 4. Display results ─────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  INCIDENT REPORT — {incident_id}")
    print(f"{'═' * 60}")

    if status == "failed":
        print(f"\n❌ Investigation FAILED: {incident.get('error')}")
        sys.exit(1)

    print_section("🎯 COMMANDER — Investigation Plan",
                  (incident.get("investigation_plan") or "")[:800] + "…")

    log_a = (incident.get("log_findings") or {}).get("analysis", "")
    print_section("🔬 LOG AGENT — Findings", log_a[:600] + ("…" if len(log_a) > 600 else ""))

    met_a = (incident.get("metrics_findings") or {}).get("analysis", "")
    print_section("📊 METRICS AGENT — Findings", met_a[:600] + ("…" if len(met_a) > 600 else ""))

    dep_a = (incident.get("deploy_findings") or {}).get("analysis", "")
    print_section("🚀 DEPLOY AGENT — Findings", dep_a[:600] + ("…" if len(dep_a) > 600 else ""))

    rca = incident.get("reasoning_summary", "")
    print_section("🧠 REASONING ENGINE — Root Cause Analysis",
                  rca[:800] + ("…" if len(rca) > 800 else ""))

    decision = incident.get("decision", "unknown")
    icon = "✅" if decision == "auto_resolve" else "🚨"
    print_section(f"{icon} DECISION — {decision.upper()}", "")

    try:
        action = json.loads(incident.get("action_taken") or "{}")
        print(json.dumps(action, indent=2))
    except Exception:
        print(incident.get("action_taken", ""))

    report = incident.get("report") or {}
    if report.get("next_steps"):
        print_section("📌 NEXT STEPS", "\n".join(f"  • {s}" for s in report["next_steps"]))

    print(f"\n{'═' * 60}")
    print(f"  Email sent : {incident.get('email_sent')}")
    print(f"  Total time : {int(time.time() - start)}s")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
