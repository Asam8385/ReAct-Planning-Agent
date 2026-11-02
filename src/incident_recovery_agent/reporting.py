
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from incident_recovery_agent.config import Settings
from incident_recovery_agent.controls import Budget
from incident_recovery_agent.schemas import (
    IncidentResult,
    Status,
    TaskState,
)


SENSITIVE_FIELDS = frozenset(
    {
        "api_key",
        "approval_secret",
        "authorization",
        "password",
        "access_token",
        "refresh_token",
    }
)


def _redact(value: Any) -> Any:
    """Remove known credential fields from structured records.

    This protects named fields. Callers must also avoid placing
    credentials inside free-text messages.
    """

    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if str(key).casefold() in SENSITIVE_FIELDS
                else _redact(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _redact(item)
            for item in value
        ]

    return value


class Reporter:
    """Record events and results for one task.

    Files are stored under:

        runtime/<task_id>/events.jsonl
        runtime/<task_id>/result.json
    """

    def __init__(
        self,
        settings: Settings,
        state: TaskState,
    ) -> None:
        self.directory = (
            settings.runtime_directory / state.task_id
        )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.events_path = (
            self.directory / "events.jsonl"
        )

        self.result_path = (
            self.directory / "result.json"
        )

    def emit(
        self,
        event: str,
        **data: Any,
    ) -> None:
        """Append an event and immediately display it in the terminal."""

        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": _redact(data),
        }

        line = json.dumps(
            record,
            ensure_ascii=False,
            default=str,
        )

        with self.events_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                line + "\n"
            )

        print(
            line,
            flush=True,
        )

    @staticmethod
    def _build_summary(
        status: Status,
        reason: str,
        last_health: str,
    ) -> str:
        """Describe the terminal outcome using recorded evidence."""

        if status == "completed":
            return (
                "The service is independently verified healthy."
            )

        if status == "unconfirmed":
            return (
                "A recovery request may have executed, but its outcome "
                "was not confirmed. Verify the current service state "
                "before retrying. "
                f"Stop reason: {reason}. "
                f"Last known health: {last_health}."
            )

        descriptions = {
            "partial": (
                "Investigation stopped before verified recovery."
            ),
            "blocked": (
                "Execution was blocked before the proposed action."
            ),
            "failed": (
                "Task execution failed."
            ),
            "cancelled": (
                "Task execution was cancelled."
            ),
        }

        description = descriptions.get(
            status,
            "Task execution stopped.",
        )

        return (
            f"{description} "
            f"Stop reason: {reason}. "
            f"Last known health: {last_health}."
        )

    def finish(
        self,
        state: TaskState,
        budget: Budget,
        status: Status,
        reason: str,
    ) -> IncidentResult:
        """Validate, save and return the final task report.

        An uncertain mutation takes precedence over other outcomes.

        Completion requires both the independent verification flag
        and a healthy observation.
        """

        if state.mutation_pending:
            status = "unconfirmed"

        elif status == "completed":
            recovery_verified = (
                state.verified_healthy
                and state.observation.get("health") == "healthy"
            )

            if not recovery_verified:
                status = "partial"
                reason = "recovery_not_verified"

        observation = _redact(
            deepcopy(state.observation)
        )

        last_health = observation.get(
            "health",
            "unknown",
        )

        result = IncidentResult(
            task_id=state.task_id,
            run_id=state.run_id,
            scenario=state.scenario,
            status=status,
            stop_reason=reason,
            summary=self._build_summary(
                status,
                reason,
                last_health,
            ),
            model_calls=budget.model_calls,
            tool_calls=budget.tool_calls,
            recovery_attempts=state.recovery_attempts,
            active_seconds=round(
                budget.active_seconds,
                3,
            ),
            last_observation=observation,
        )

        # Write to a temporary file before replacing the final report.
        temporary_path = self.result_path.with_suffix(
            ".json.tmp"
        )

        temporary_path.write_text(
            result.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            self.result_path
        )

        self.emit(
            "finished",
            **result.model_dump(mode="json"),
        )

        return result