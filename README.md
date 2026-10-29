# Incident Diagnosis and Recovery Agent

One uv-managed Python project, two local processes: a LangChain agent
and a FastMCP HTTP server backed by a deterministic Python simulator.

## Scaffold status

Configuration, environment checks, incident fixtures, documentation,
package entry points and test locations are included. Agent, MCP server,
simulator, approval enforcement and runtime controls are implementation
boundaries, not working features yet. Entry points fail explicitly
until implemented. Fixture tests validate data only, not agent behavior.

## Setup

Run from this project root:

```bash
uv python install 3.12
uv sync
uv run python scripts/check_environment.py
uv run pytest
uv run ruff check .
```

Copy `.env.example` to `.env` with your editor when configuration changes
are needed. Defaults are available in config.py. uv creates .venv and
uv.lock; commit uv.lock. The scaffolder never fabricates either file.
No global pip install, manual virtualenv activation or requirements.txt
is needed for the uv project workflow.

## Implementation order

1. Confirm the environment using check_environment.py.
2. Implement the simulator; verify state transitions without an LLM.
3. Expose simulator operations via one local FastMCP HTTP endpoint.
4. Verify tool discovery and calls over HTTP without an LLM.
5. Connect one LangChain agent through mcp_client.py.
6. Implement budgets, approvals, verification and fallback reporting.
7. Verify successful, blocked, failed and budget-exhausted scenarios.

## Intended commands after implementation

- Terminal 1: `uv run incident-mcp`
- Terminal 2: `uv run incident-agent`

These commands currently return an explicit scaffold-only error.
The MCP server should bind to 127.0.0.1:8000, path /mcp, using
Streamable HTTP. It owns simulated state; the agent accesses that
state through MCP rather than importing the simulator directly.

## Model integration

Select and add the model-provider integration before implementing the
agent. No provider credentials or default paid model are assumed.
The current LangChain built-in MCP adapter is beta; isolate its use in
mcp_client.py and lock the tested dependency set with uv.lock.

See docs/architecture.md and docs/acceptance.md for the implementation
contract. Source scenario JSON files are immutable initial conditions;
changing them must not be used to fake recovery outcomes.
