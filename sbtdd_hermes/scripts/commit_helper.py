"""
Commit message helper.
"""


# Commit prefixes by phase
COMMIT_PREFIXES = {
    "red": "test:",
    "green": "feat:",
    "refactor": "refactor:",
    "close_task": "chore:",
}


def suggest_commit(phase: str, task: str, description: str = "") -> str:
    """Generate a suggested commit message."""
    prefix = COMMIT_PREFIXES.get(phase, "chore:")
    
    if phase == "red":
        return f"{prefix} add test for {task}"
    elif phase == "green":
        return f"{prefix} implement {task}"
    elif phase == "refactor":
        return f"{prefix} clean up {task}"
    elif phase == "close_task":
        return f"{prefix} mark task {task} as complete"
    else:
        return f"{prefix} {task}"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SBTDD Commit Message Helper")
    parser.add_argument("--phase", required=True, choices=["red", "green", "refactor", "close_task"])
    parser.add_argument("--task", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    print(suggest_commit(args.phase, args.task, args.description))


if __name__ == "__main__":
    main()
