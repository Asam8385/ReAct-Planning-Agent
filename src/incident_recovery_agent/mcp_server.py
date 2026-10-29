"""Expose simulator tools through FastMCP Streamable HTTP on localhost.

Planned tools: start_incident, check_health, read_logs, get_runbook,
apply_recovery. Every operation after initialization uses run_id.
Recovery authorization and attempt limits must be enforced here.
"""


def main() -> None:
    raise SystemExit(
        "Scaffold only: implement the simulator and FastMCP tools first."
    )
