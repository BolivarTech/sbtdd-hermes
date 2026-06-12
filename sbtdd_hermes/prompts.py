"""
Prompt generators for the agent.
Builds structured prompts/instructions based on current state.
"""

# Placeholder - will be filled in Task 4

def build_phase_prompt(phase: str, state) -> str:
    return f"Phase: {phase} (placeholder)"

def build_verification_prompt(stack: str) -> str:
    return f"Verification for {stack} (placeholder)"

def build_git_status_prompt() -> str:
    return "Git status check (placeholder)"

def build_commit_suggestion(phase: str, task_id: str, description: str) -> str:
    return f"[{phase}] {task_id}: {description} (placeholder)"

def build_pre_merge_checklist() -> str:
    return "Pre-merge checklist (placeholder)"

def build_magi_payload(spec_path, plan_path) -> str:
    return "MAGI payload (placeholder)"
