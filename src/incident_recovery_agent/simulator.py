"""Deterministic service environment for incident investigation.

Each incident has independent state identified by run_id.

The MCP server verifies recovery authorization before calling recover().
This module enforces action prerequisites, state versions, attempt limits,
and operation replay protection.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from uuid import uuid4

from incident_recovery_agent.schemas import (
    Action,
    HealthResult,
    LogsResult,
    RecoveryResult,
    RunbookResult,
)


SERVICE_NAME = "reporting-service"

SCENARIOS: dict[str, str] = {
    "healthy": "running",
    "stopped_service": "stopped",
    "configuration_error": "invalid_config",
    "cache_pressure": "cache_full",
    "persistent_failure": "dependency_down",
}

INITIAL_LOGS: dict[str, list[str]] = {
    "running": [
        "INFO reporting-service started successfully",
        "INFO health endpoint returns HTTP 200",
    ],
    "stopped": [
        "ERROR reporting-service process is not running",
        "ERROR health endpoint is unavailable",
    ],
    "invalid_config": [
        "ERROR startup failed",
        "ERROR invalid configuration key: REPORT_MODE",
    ],
    "cache_full": [
        "ERROR cache capacity exceeded",
        "ERROR incoming requests rejected",
    ],
    "dependency_down": [
        "ERROR required upstream dependency is unavailable",
        "ERROR dependency requires intervention outside this service",
    ],
}

RUNBOOK: dict[Action, str] = {
    "restart_service": (
        "Restart a stopped service process. "
        "A restart does not repair invalid configuration, "
        "clear an exhausted cache, or restore an upstream dependency."
    ),
    "restore_config": (
        "Restore the known-good service configuration and start "
        "the service. Use when logs identify invalid configuration."
    ),
    "clear_cache": (
        "Clear the simulated application cache. "
        "Use when logs report cache capacity exhaustion."
    ),
}

RECOVERY_TRANSITIONS: dict[tuple[str, str], str] = {
    ("stopped", "restart_service"): "running",
    ("invalid_config", "restore_config"): "running",
    ("cache_full", "clear_cache"): "running",
}


@dataclass
class _RecoveryRecord:
    """Stored result of one uniquely identified recovery operation."""

    action: str
    version: int
    result: dict[str, Any]


@dataclass
class _ServiceRun:
    """Private mutable state belonging to one simulated incident."""

    phase: str
    logs: list[str] = field(default_factory=list)

    version: int = 0
    recovery_attempts: int = 0

    health_checked: bool = False
    logs_read: bool = False
    runbook_read: bool = False

    operations: dict[str, _RecoveryRecord] = field(
        default_factory=dict,
    )


class Simulator:
    """Thread-safe, in-memory service simulator.

    Restarting the server clears its incident state.
    Unknown run IDs fail explicitly instead of silently creating a new run.
    """

    def __init__(
        self,
        max_recoveries: int = 2,
    ) -> None:
        if (
            isinstance(max_recoveries, bool)
            or not isinstance(max_recoveries, int)
            or max_recoveries < 1
        ):
            raise ValueError(
                "max_recoveries must be a positive integer"
            )

        self.max_recoveries = max_recoveries

        self._runs: dict[str, _ServiceRun] = {}
        self._lock = RLock()

    def _get(
        self,
        run_id: str,
    ) -> _ServiceRun:
        """Retrieve a run while the caller holds the lock."""

        if run_id not in self._runs:
            raise ValueError(
                "Unknown run_id; the server may have restarted"
            )

        return self._runs[run_id]

    def _snapshot(
        self,
        run_id: str,
        run: _ServiceRun,
    ) -> dict[str, Any]:
        """Build a validated copy of the current service state."""

        return HealthResult(
            run_id=run_id,
            service=SERVICE_NAME,
            phase=run.phase,
            health=(
                "healthy"
                if run.phase == "running"
                else "unhealthy"
            ),
            version=run.version,
            recovery_attempts=run.recovery_attempts,
        ).model_dump()

    def start(
        self,
        scenario: str,
    ) -> dict[str, Any]:
        """Create an independent incident from a supported scenario."""

        with self._lock:
            if scenario not in SCENARIOS:
                choices = ", ".join(
                    sorted(SCENARIOS)
                )

                raise ValueError(
                    f"Unknown scenario. Supported scenarios: {choices}"
                )

            phase = SCENARIOS[scenario]
            run_id = uuid4().hex

            run = _ServiceRun(
                phase=phase,
                logs=list(INITIAL_LOGS[phase]),
            )

            self._runs[run_id] = run

            return self._snapshot(
                run_id,
                run,
            )

    def health(
        self,
        run_id: str,
    ) -> dict[str, Any]:
        """Independently inspect the current service health."""

        with self._lock:
            run = self._get(run_id)
            run.health_checked = True

            return self._snapshot(
                run_id,
                run,
            )

    def logs(
        self,
        run_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Return a bounded copy of the latest diagnostic log entries."""

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 20
        ):
            raise ValueError(
                "limit must be an integer between 1 and 20"
            )

        with self._lock:
            run = self._get(run_id)
            run.logs_read = True

            return LogsResult(
                **self._snapshot(run_id, run),
                logs=list(run.logs[-limit:]),
            ).model_dump()

    def runbook(
        self,
        run_id: str,
    ) -> dict[str, Any]:
        """Return permitted recovery actions and their intended use."""

        with self._lock:
            run = self._get(run_id)
            run.runbook_read = True

            return RunbookResult(
                **self._snapshot(run_id, run),
                actions=dict(RUNBOOK),
            ).model_dump()

    def recover(
        self,
        run_id: str,
        action: str,
        version: int,
        operation_id: str,
    ) -> dict[str, Any]:
        """Apply one recovery after server-side authorization.

        Repeating an identical operation_id returns its stored result
        without applying the recovery or consuming another attempt.

        A permitted but ineffective action still consumes an attempt.
        The caller must check health afterward.
        """

        with self._lock:
            run = self._get(run_id)

            if not operation_id.strip():
                raise ValueError(
                    "operation_id must not be empty"
                )

            previous = run.operations.get(
                operation_id
            )

            if previous is not None:
                if (
                    previous.action != action
                    or previous.version != version
                ):
                    raise ValueError(
                        "operation_id already belongs to a different request"
                    )

                return deepcopy(
                    previous.result
                )

            if action not in RUNBOOK:
                raise ValueError(
                    "Recovery action is not allowed"
                )

            if (
                isinstance(version, bool)
                or not isinstance(version, int)
                or version < 0
            ):
                raise ValueError(
                    "version must be a non-negative integer"
                )

            if version != run.version:
                raise ValueError(
                    "Service state changed; collect fresh evidence "
                    "and obtain new approval"
                )

            prerequisites_met = (
                run.health_checked
                and run.logs_read
                and run.runbook_read
            )

            if not prerequisites_met:
                raise ValueError(
                    "Check health, read logs and consult the runbook "
                    "before requesting recovery"
                )

            if run.phase == "running":
                raise ValueError(
                    "Service is already healthy"
                )

            if (
                run.recovery_attempts
                >= self.max_recoveries
            ):
                raise ValueError(
                    "Server recovery limit reached"
                )

            previous_phase = run.phase

            run.phase = RECOVERY_TRANSITIONS.get(
                (previous_phase, action),
                previous_phase,
            )

            run.recovery_attempts += 1
            run.version += 1

            # Fresh health and logs are required before another recovery.
            run.health_checked = False
            run.logs_read = False

            run.logs.append(
                f"INFO recovery action executed: {action}"
            )

            if run.phase == "running":
                run.logs.append(
                    "INFO service transitioned to running"
                )
            else:
                run.logs.append(
                    f"WARNING service remains in phase: {run.phase}"
                )

            result = RecoveryResult(
                **self._snapshot(run_id, run),
                action=action,
                message=(
                    "Recovery action executed. "
                    "Perform an independent health check "
                    "to verify the outcome."
                ),
            ).model_dump()

            run.operations[operation_id] = _RecoveryRecord(
                action=action,
                version=version,
                result=deepcopy(result),
            )

            return result