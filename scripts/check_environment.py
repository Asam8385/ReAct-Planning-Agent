"""Check the active Python environment; no network or API requests are made."""

import importlib.util
import shutil
import sys
from importlib import metadata
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = []
    print(f"Python: {sys.version.split()[0]}")
    print(f"Interpreter: {sys.executable}")
    print(f"Project: {root}")
    if sys.version_info < (3, 12):
        failures.append("Python 3.12 or newer is required")
    project_environment = root / ".venv"
    if Path(sys.prefix).resolve() != project_environment.resolve():
        failures.append("Run this check using uv run python scripts/check_environment.py")
    print(f"Active environment: {sys.prefix}")
    uv_path = shutil.which("uv")
    print(f"uv: {uv_path or 'not found'}")
    if uv_path is None:
        failures.append("uv is not available on PATH")
    packages = {
        "fastmcp": "fastmcp",
        "langchain": "langchain",
        "langgraph": "langgraph",
        "pydantic-settings": "pydantic_settings",
        "rich": "rich",
        "incident-recovery-agent": "incident_recovery_agent",
    }
    for distribution, module in packages.items():
        try:
            version = metadata.version(distribution)
            if importlib.util.find_spec(module) is None:
                raise ModuleNotFoundError(module)
            print(f"OK  {distribution}: {version}")
        except (metadata.PackageNotFoundError, ModuleNotFoundError):
            print(f"MISSING  {distribution}")
            failures.append(f"Install {distribution} with uv sync")
    if (root / "uv.lock").is_file():
        print("OK  uv.lock exists")
    else:
        failures.append("uv.lock is missing; run uv sync")
    print("INFO  Model-provider integration will be added when the model is selected.")
    print("INFO  No model endpoint or MCP server connectivity was tested.")
    if failures:
        print("\nEnvironment check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nEnvironment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
