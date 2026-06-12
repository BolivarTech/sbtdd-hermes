"""
Git status analyzer.
"""

import json
import subprocess


def check_git_status() -> dict:
    """Run git status and return parsed results."""
    result = {
        "has_changes": False,
        "modified": [],
        "staged": [],
        "untracked": [],
        "last_commit_prefix": None,
        "last_commit_message": None,
    }
    
    # git status --short
    ok, output = _run(["git", "status", "--short"])
    if ok and output.strip():
        result["has_changes"] = True
        for line in output.strip().splitlines():
            status = line[:2]
            path = line[3:]
            if status.startswith("M") or status.startswith("A"):
                result["staged"].append(path)
            elif status.startswith(" M") or status.startswith(" D"):
                result["modified"].append(path)
            elif status.startswith("??"):
                result["untracked"].append(path)
    
    # git log --oneline -1
    ok, output = _run(["git", "log", "--format=%s", "-1"])
    if ok and output.strip():
        msg = output.strip()
        result["last_commit_message"] = msg
        result["last_commit_prefix"] = msg.split(":")[0] if ":" in msg else msg.split()[0]
    
    return result


def get_git_log(n: int = 5) -> list[dict]:
    """Return last N commits."""
    ok, output = _run(["git", "log", "--oneline", f"-n{n}"])
    if not ok:
        return []
    
    commits = []
    for line in output.strip().splitlines():
        if " " in line:
            sha, msg = line.split(" ", 1)
            commits.append({"sha": sha, "message": msg})
    return commits


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SBTDD Git Status Analyzer")
    parser.add_argument("--check", action="store_true", help="Check git status for /sbtdd-check")
    parser.add_argument("--log", type=int, help="Show last N commits")
    parser.add_argument("--last-prefix", action="store_true", help="Show last commit prefix")
    args = parser.parse_args()
    
    if args.log:
        print(json.dumps(get_git_log(args.log), indent=2))
    elif args.last_prefix:
        status = check_git_status()
        print(status.get("last_commit_prefix", "N/A"))
    else:
        print(json.dumps(check_git_status(), indent=2))


if __name__ == "__main__":
    main()
