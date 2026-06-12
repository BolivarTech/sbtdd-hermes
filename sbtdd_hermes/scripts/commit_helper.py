"""
Commit message helper.
"""

import sys


def suggest_commit(phase: str, task: str) -> str:
    """Generate a suggested commit message."""
    # TODO: implement commit message generation
    return f"[{phase}] {task}"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    print(suggest_commit(args.phase, args.task))


if __name__ == "__main__":
    main()
