import hmac 
from collections.abc import Callable
from typing import Any


from fastmcp import FastMCP
from pydantic import ValidationError

from incident_recovery_agent.config import Settings
from incident_recovery_agent.controls import recovery_signature
from incident_recovery_agent.schemas import RecoveryRequest
from incident_recovery_agent.simulator import Simulator



def _execute(
    operation: Callable[..., dict[str, Any]],
    *arguments: Any,
) -> dict[str, Any]:
    """Convert expected simulator failures into structured responses."""

    try:
        return operation(*arguments)

    except ValueError as error:
        return {
            "ok": False,
            "error": str(error),
        }


def build_server(settings: Settings) -> FastMCP:
    """Construct one MCP server with its own simulated incident state."""

    # Fail during startup if the shared signing secret is missing.
    signing_secret = settings.signing_key()

    simulator = Simulator(
        max_recoveries=settings.max_recovery_attempts,
    )

    server = FastMCP(
        "Incident Diagnosis and Recovery Tools"
    )

    @server.tool()
    def start_incident(
        scenario: str,
    ) -> dict[str, Any]:
        """Initialize an independent simulated incident.

        Returns the incident run_id and initial service state.
        The application runner calls this once before agent execution.
        """

        return _execute(
            simulator.start,
            scenario,
        )

    @server.tool()
    def check_health(
        run_id: str,
    ) -> dict[str, Any]:
        """Independently inspect the incident's current service health.

        Call this before recovery and again after recovery.
        A healthy result provides verification of service recovery.
        """

        return _execute(
            simulator.health,
            run_id,
        )

    @server.tool()
    def read_logs(
        run_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Read the latest diagnostic logs for an incident.

        limit must be an integer between 1 and 20.
        Fresh logs are required before another recovery attempt.
        """

        return _execute(
            simulator.logs,
            run_id,
            limit,
        )

    @server.tool()
    def get_runbook(
        run_id: str,
    ) -> dict[str, Any]:
        """Read permitted recovery actions and their intended use.

        Consult this guidance before proposing a recovery action.
        """

        return _execute(
            simulator.runbook,
            run_id,
        )

    @server.tool()
    def apply_recovery(
        run_id: str,
        action: str,
        version: int,
        operation_id: str,
        authorization: str,
    ) -> dict[str, Any]:
        """Execute one recovery authorized by the trusted application.

        Authorization binds the incident, action, expected state version,
        and operation ID.

        Repeating an identical operation ID returns its stored result
        without applying the recovery again.
        """

        try:
            request = RecoveryRequest(
                run_id=run_id,
                action=action,
                version=version,
                operation_id=operation_id,
                authorization=authorization,
            )

        except ValidationError:
            # Do not return validation details containing authorization.
            return {
                "ok": False,
                "error": "Invalid recovery request.",
            }

        expected_signature = recovery_signature(
            secret=signing_secret,
            run_id=request.run_id,
            action=request.action,
            version=request.version,
            operation_id=request.operation_id,
        )

        authorized = hmac.compare_digest(
            request.authorization.encode("utf-8"),
            expected_signature.encode("ascii"),
        )

        if not authorized:
            return {
                "ok": False,
                "error": (
                    "Missing or invalid recovery authorization."
                ),
            }

        # The simulator independently checks prerequisites, state version,
        # permitted actions, recovery limits, and operation replay.
        return _execute(
            simulator.recover,
            request.run_id,
            request.action,
            request.version,
            request.operation_id,
        )

    return server


def main() -> None:
    """Start the local Streamable HTTP MCP server."""

    settings = Settings()

    server = build_server(
        settings
    )

    server.run(
        transport="http",
        host=settings.host,
        port=settings.port,
        path="/mcp",
        show_banner=False,
    )


if __name__ == "__main__":
    main()
