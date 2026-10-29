"""Validate scenario fixtures; these are not agent behavior tests."""

import json
from pathlib import Path


def test_scenario_contract():
    root = Path(__file__).resolve().parents[2] / "data" / "scenarios"
    scenarios = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted(root.glob("*.json"))]
    assert len(scenarios) == 4
    assert len({item["id"] for item in scenarios}) == len(scenarios)
    for item in scenarios:
        states = item["states"]
        assert item["initial_state"] in states
        assert item["expected_status"] in {"completed", "partial"}
        assert states
        for state in states.values():
            assert state["health"] in {"healthy", "unhealthy"}
            assert isinstance(state["logs"], list)
            for action, target in state["transitions"].items():
                assert action in item["allowed_actions"]
                assert target in states
