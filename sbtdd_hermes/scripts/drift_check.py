"""
Drift checker between session-state.json and git log.
"""

import json
import sys
from pathlib import Path


def check_drift(state_path: Path) -> dict:
    """Detect drift between state and git history."""
    # TODO: implement drift detection
    return {"drift": "placeholder"}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=".hermes/session-state.json")
    args = parser.parse_args()
    print(json.dumps(check_drift(Path(args.state))))


if __name__ == "__main__":
    main()
