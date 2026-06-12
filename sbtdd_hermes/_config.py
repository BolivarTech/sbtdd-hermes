import os

# === TDD-Guard ===
TDDGUARD_TOOL_NAMES = {"write_file", "patch", "terminal"}
TDDGUARD_TEST_PATTERNS = [
    r"tests?/",
    r"test_[^/]+\.py$",
    r"[^/]+_test\.py$",
]
TDDGUARD_CONFIDENCE_THRESHOLD = 0.7
MAX_OVERRIDE_PER_SESSION = 3

# === Timeouts ===
SCRIPT_TIMEOUT = 60
MAGI_PARSE_TIMEOUT = 5.0

# === State ===
STATE_SCHEMA_VERSION = 1

# === MAGI Parser ===
MAGI_SUPPORTED_FORMATS = ["2.0"]
MAGI_BANNER_RE = r"\+={52}\+"
MAGI_VEREDICTO_RE = r"\|\s+CONSENSUS:\s+([^|]+)\s+\|"
MAGI_FINDING_RE = r"\[([!]+)\]\s+\[(\w+)\]\s+([^\n]*)"

# === Phase State Machine ===
PHASE_TRANSITIONS = {
    "red": {"green", "done"},
    "green": {"refactor", "done"},
    "refactor": {"red", "done"},
    "done": set(),
}
VALID_PHASES = set(PHASE_TRANSITIONS.keys())

# === Update Whitelist (agent can mutate) ===
STATE_UPDATE_FIELDS = {
    "magi_iterations_used": {"type": int, "min": 0, "max": 999},
    "magi_iteration_budget": {"type": int, "min": 1, "max": 99},
    "magi_target_verdict": {
        "type": str,
        "choices": {
            "STRONG GO", "GO", "GO WITH CAVEATS",
            "HOLD", "HOLD -- TIE", "STRONG NO-GO",
        }
    },
    "current_phase": {"type": str, "validate": "phase_transition"},
    "notes": {"type": str, "max_length": 1000},
}

# === Cross-field Validators ===
CROSS_FIELD_VALIDATORS = [
    ("magi_iterations_used", "magi_iteration_budget",
     lambda u, b: b is None or u <= b,
     "magi_iterations_used ({u}) exceeds budget ({b})"),
    ("last_verification_at", "phase_started_at_commit",
     lambda v, c: c == "" or v is None or v >= c,
     "last_verification_at ({v}) before phase_started_at_commit ({c})"),
]

# === Strict Mode ===
STRICT_MODE = os.environ.get("SBTDD_STRICT", "false").lower() == "true"

# === Retry Config ===
FILELOCK_RETRY_ATTEMPTS = 3
FILELOCK_RETRY_DELAYS = [0.1, 0.5, 1.0]
