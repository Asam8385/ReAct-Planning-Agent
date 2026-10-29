# Architecture and implementation contract

## Boundaries

One Python project contains two runnable processes. The agent uses
LangChain and an MCP client. The FastMCP server owns simulator state
and exposes a Streamable HTTP endpoint. No browser, operating-system
service control or live infrastructure access is required.

## Adaptive decisions and fixed constraints

The model chooses diagnostic tools and proposes recovery based on
tool observations. Python validates every transition and enforces
limits. A separate reviewer model is unnecessary. Brief action
summaries and tool evidence provide visibility into each decision.

## Workflow

initialize -> investigate -> propose recovery -> approval -> apply
-> verify. Verification can return to investigation within the same
task budget. Every stage may terminate as blocked, failed, cancelled,
partial or completed. Ordinary questions can receive a direct answer.

## Simulator

Source JSON describes initial conditions and action transitions.
start_incident creates a fresh, independent run state. Health and
logs reflect that run's current state. apply_recovery mutates only
that state and appends an event. check_health is independent evidence
of recovery: tool execution alone does not establish success.

State is keyed by explicit run_id, not an HTTP connection or MCP
session. A server restart must make a lost run explicit, never reset
it silently. The agent must not import simulator internals. Reset and
fault injection are operator controls, not unrestricted agent tools.

## Tools

- start_incident(scenario_id): initialize once; return run_id.
- check_health(run_id): return current status and state version.
- read_logs(run_id, limit): return bounded diagnostic observations.
- get_runbook(run_id): return permitted actions and preconditions.
- apply_recovery(run_id, action, authorization): validate and apply.

## Approval and limits

The agent process owns a task-wide model/tool/deadline budget.
The server enforces permitted actions, recovery attempts, and
authorization. Authorization must come from trusted approval handling,
never from a model-supplied approved=true argument. An approval binds
to one run, action and state version, and is consumed once.
Configure invocation and task-wide limits so resume cannot replenish
the task budget. Count invalid calls, failed calls and retries.

Active deadlines exclude human waiting. Individual model and MCP
calls also have deadlines. Client timeout alone does not prove that
server execution stopped: reconcile a mutation before retrying.
Detect repeated actions with unchanged state as a no-progress signal.

## Reporting

Record task ID, scenario, observation, tool arguments/results,
approval, attempts, elapsed active time and stop reason. Reports
are generated from state even if no model call is available.
Simulator scenario metadata containing hidden expected outcomes is
for the test harness and must not be returned as diagnostic evidence.
