import hashlib
import hmac
import json 
from collections import Counter
from contextlib import contextmanager
from time import monotonic
from typing import Any, Iterator

from incident_recovery_agent.schemas import Status
from incident_recovery_agent.config import Settings


class StopTask(Exception):

   def __init__(self, 
         reason: str,
         status : Status = "partial"
   ):
      super.__init__(reason)

      self.reason = reason
      self.status = status


class Budget:

   def __init__(self, settings: Settings) -> None:

      self.settings = settings

      self.model_calls = 0
      self.tool_calls = 0 

      self.started = monotonic()
      self.paused_seconds = 0.0

      self._pause_started: float | None = None
      self._pause_depth = 0

      self.last_phase : str | None = None

      self.repeated: Counter[str] = Counter()


   @property
   def  active_seconds(self) -> float:

      now = monotonic()

      current_pause = (

         now - self._pause_started if self._pause_started is not None else 0.0
      )

      return max(
         0.0,
         now - self.started - self.paused_seconds - current_pause,
      )


   def remaining(self) -> float:

      seconds = (
         self.settings.active_timeout_seconds
      )

      if seconds <= 0:
         raise StopTask(
            reason="active_deadline",
         )

      return seconds


   def model_call(self) -> None:

      self.remaining()

      if self.model_calls >= self.settings.max_model_calls:
         raise StopTask(
            reason="model_calll_limit",
         )


      self.model_call +=1


   def tool_call(self) -> None:
        """Reserve one tool attempt before validating or executing it."""

        self.remaining()

        if self.tool_calls >= self.settings.max_tool_calls:
            raise StopTask(
                reason="tool_call_limit",
            )

        self.tool_calls += 1


   @contextmanager
   def pause(self) -> Iterator[None]:

      if self._pause_depth == 0:
         self._pause_started = monotonic()

      self._pause_depth += 1 

      try: 
         yield

      finally:
         self._pause_depth -= 1

         if self._pause_depth == 0:
            if self._pause_started is not None:
               self.paused_seconds += (

                  monotonic() - self._pause_started
               ) 

            self._pause_started = None 



   def observe(
        self,
        name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Detect repeated requests while service phase stays unchanged.

        A changed phase clears repetition history. Within one phase,
        matching tool names, arguments and errors share a counter.

        This is a no-progress heuristic. Model, tool and time budgets
        provide independent limits even when requests vary.
        """

        phase = result.get(
            "phase",
            self.last_phase,
        )

        if phase != self.last_phase:
            self.repeated.clear()
            self.last_phase = phase

        fingerprint = json.dumps(
            [
                name,
                arguments,
                phase,
                result.get("error"),
            ],
            sort_keys=True,
            separators=(",", ":"),
        )

        self.repeated[fingerprint] += 1

        if (
            self.repeated[fingerprint]
            >= self.settings.no_progress_limit
        ):
            raise StopTask(
                reason="no_progress",
            )


def recovery_signature(
    secret: str,
    run_id: str,
    action: str,
    version: int,
    operation_id: str,
) -> str:
    """Sign one exact recovery request using HMAC-SHA256.

    The trusted application creates this signature after approval.
    The MCP server independently calculates and verifies it.

    Operation replay protection and state-version validation belong
    to the server and simulator.
    """

    payload = json.dumps(
        [
            run_id,
            action,
            version,
            operation_id,
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()





   



      
      
      