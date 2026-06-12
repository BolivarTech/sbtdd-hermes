"""
Drift checker between session-state.json and git log.
"""

import json
import subprocess
import sys
from pathlib import Path

from .git_status import check_git_status, get_git_log


def check_drift(state_path: Path) -> dict:
    """Detect drift between state and git history."""
    # Load state
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "classification": "N/A",
            "reason": "No state file found",
            "expected_phase": None,
            "actual_phase": None,
        }
    
    state_phase = state.get("current_phase", "unknown")
    
    # Get last commit prefix
    git_status = check_git_status()
    last_prefix = git_status.get("last_commit_prefix", "")
    
    # Map commit prefix to expected phase
    prefix_to_phase = {
        "test:": "red",
        "feat:": "green",
        "fix:": "green",
        "refactor:": "refactor",
        "chore:": "refactor",  # close task
    }
    
    expected_phase = prefix_to_phase.get(last_prefix, "unknown")
    
    # Classify
    if expected_phase == "unknown":
        classification = "UNRECOGNISED"
        reason = f"Unrecognised commit prefix: {last_prefix}"
    elif expected_phase == state_phase:
        classification = "CONSISTENT"
        reason = f"State phase ({state_phase}) matches commit prefix ({last_prefix})"
    elif _is_recoverable(state_phase, expected_phase):
        classification = "RECOVERABLE_LAG"
        reason = f"State phase ({state_phase}) is behind commit prefix ({last_prefix}); may recover"
    else:
        classification = "DRIFT"
        reason = f"State phase ({state_phase}) conflicts with commit prefix ({last_prefix})"
    
    return {
        "classification": classification,
        "reason": reason,
        "expected_phase": expected_phase,
        "actual_phase": state_phase,
        "last_prefix": last_prefix,
    }


def _is_recoverable(state_phase: str, expected_phase: str) -> bool:
    """Check if state is behind but recoverable."""
    # If state is "red" but commit shows "refactor", we're behind but not drifted
    order = {"red": 0, "green": 1, "refactor": 2, "done": 3}
    return order.get(state_phase, -1) < order.get(expected_phase, -1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SBTDD Drift Checker")
    parser.add_argument("--state", default=".hermes/session-state.json")
    args = parser.parse_args()
    print(json.dumps(check_drift(Path(args.state)), indent=2))


if __name__ == "__main__":
    main()
