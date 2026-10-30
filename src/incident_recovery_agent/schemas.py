from dataclasses import dataclass , field
from typing import Any , Literal

from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

Action = Literal[
    "restart_service",
    "restore_config",
    "clear_cache",
]

Scenario = Literal[
    "healthy",
    "stopped_service",
    "configuration_error",
    "cache_pressure",
    "persistent_failure",
]

HealthStatus = Literal[
    "healthy",
    "unhealthy",
]

Status = Literal[
    "completed",
    "partial",
    "blocked",
    "failed",
    "cancelled",
    "unconfirmed",
]



class ApplicationModel(BaseModel):

   model_config = ConfigDict(
      extra="forbid",
      validate_assignment=True # during all the time reassigning the value it will trigger
   )


# Task input

class IncidentRequest(ApplicationModel):

   scenario : Scenario = "stopped_service"

   task: str = Field(
        default=(
            "Diagnose this incident and restore service if permitted."
        ),
        min_length=1,
        max_length=4000,
    )


# Successful MCP responses (tool call)

class HealthResult(ApplicationModel):
    """A snapshot of a simulated service.

    The snapshot describes service state. Whether it constitutes
    independent verification depends on which tool produced it.
    """

    ok: Literal[True] = True

    run_id: str = Field(
        min_length=1,
    )

    service: str = Field(
        min_length=1,
    )

    phase: str = Field(
        min_length=1,
    )

    health: HealthStatus

    version: int = Field(
        ge=0,
    )

    recovery_attempts: int = Field(
        ge=0,
    )


class LogsResult(HealthResult):

   logs: list[str] = Field(
      default_factory=list,
      max_length=20
   )





class RecoveryProposal(ApplicationModel):
    """The exact recovery operation presented for human approval."""

    run_id: str = Field(
        min_length=1,
    )

    action: Action

    version: int = Field(
        ge=0,
    )


class RecoveryRequest(RecoveryProposal):
    """A recovery proposal authorized by the trusted application.

    The operation ID identifies this particular execution request.

    Authorization is generated after approval. It must not be
    supplied by the language model.

    repr=False prevents authorization from appearing in the
    model's normal representation. Serialization and logging
    must still exclude it explicitly when appropriate.
    """

    operation_id: str = Field(
        min_length=1,
    )

    authorization: str = Field(
        min_length=1,
        repr=False,
    )


@dataclass
class TaskState:
    """Execution state belonging to one agent task.

    Each instance receives its own task ID and observation dictionary.
    This state is held in memory for the lifetime of the task.
    """

    scenario: str

    task_id: str = field(
        default_factory=lambda: uuid4().hex,
    )

    run_id: str = ""

    observation: dict[str, Any] = field(
        default_factory=dict,
    )

    # True only after a successful independent health check.
    verified_healthy: bool = False

    # Remains true if a submitted recovery has an uncertain outcome.
    mutation_pending: bool = False

    # Latest recovery count observed from the MCP server.
    recovery_attempts: int = 0

    # Evidence collected before a recovery proposal.
    health_checked: bool = False
    logs_read: bool = False
    runbook_read: bool = False




class RunbookResult(HealthResult):
    """Service state with permitted recovery actions and guidance."""

    actions: dict[Action, str] = Field(
        default_factory=dict,
    )


class RecoveryResult(HealthResult):
    """Result of executing a recovery action.

    Execution success does not guarantee service recovery.
    A subsequent health check must verify the outcome.
    """

    action: Action

    message: str = Field(
        min_length=1,
    )



class IncidentResult(ApplicationModel):
    """Final report generated from recorded execution state."""

    task_id: str = Field(
        min_length=1,
    )

    # Empty if initialization failed before creating an incident.
    run_id: str = ""

    scenario: str = Field(
        min_length=1,
    )

    status: Status

    stop_reason: str = Field(
        min_length=1,
    )

    summary: str = Field(
        min_length=1,
    )

    model_calls: int = Field(
        ge=0,
    )

    tool_calls: int = Field(
        ge=0,
    )

    recovery_attempts: int = Field(
        ge=0,
    )

    active_seconds: float = Field(
        ge=0,
    )

    last_observation: dict[str, Any] = Field(
        default_factory=dict,
    )




