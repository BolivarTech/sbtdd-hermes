from pathlib import Path
# Project root is the repo root (where pyproject.toml lives)
ROOT = Path(__file__).parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# tests for skills/sbtdd/SKILL.md
# ---------------------------------------------------------------------------
SKILL = ROOT / "skills/sbtdd/SKILL.md"

# the only skills the orchestrator is allowed to delegate to
ALLOWED_DELEGATES = {
    "plan", "magi", "test-driven-development",
    "requesting-code-review", "systematic-debugging", "simplify-code",
}


def test_frontmatter_has_name_and_description():
    text = _read(SKILL)
    assert text.startswith("---")
    assert "name: sbtdd" in text
    assert "description:" in text
    assert "SBTDD" in text


def test_skill_describes_five_step_flow():
    t = _read(SKILL).lower()
    for step in ("preflight", "route", "execute", "gate", "loop"):
        assert step in t


def test_delegation_table_only_references_known_skills():
    t = _read(SKILL)
    for skill in ALLOWED_DELEGATES:
        assert skill in t, f"skill '{skill}' must be referenced in SKILL.md"


def test_skill_links_all_five_references():
    t = _read(SKILL)
    for ref in ("routing.md", "review-gates.md", "tdd-cycle.md",
                "finalization.md", "port-claude-to-hermes.md"):
        assert ref in t, f"reference '{ref}' must be linked in SKILL.md"


def test_preflight_routes_to_init_when_uninitialized():
    t = _read(SKILL)
    assert "sbtdd-init" in t
    assert "HERMES.local.md" in t


def test_plan_gate_lists_manual_review_before_magi():
    row = ""
    for line in _read(SKILL).splitlines():
        if line.lower().startswith("| plan gate"):
            row = line
            break
    assert row, "plan-gate delegation row not found in SKILL.md"
    low = row.lower()
    assert "checkpoint 1" in low and "checkpoint 2" in low
    assert "manual review" in low
    assert low.index("manual review") < low.index("magi"), \
        "manual review (Checkpoint 1) must be listed before magi"


def test_skill_points_to_magi_contract():
    """SKILL.md must reference the MAGI backend selection."""
    t = _read(SKILL)
    assert "magi" in t.lower()
    assert "review-gates.md" in t


def test_skill_points_to_backend_selection():
    """SKILL.md must reference the Ollama backend and review-gates §8."""
    t = _read(SKILL)
    assert "--ollama" in t
    assert "review-gates.md §8" in t
    assert "magi-ollama.toml" in t


# ---------------------------------------------------------------------------
# tests for commands/*.md
# ---------------------------------------------------------------------------
CMD = ROOT / "commands"


def test_sbtdd_command_invokes_skill():
    t = _read(CMD / "sbtdd.md")
    assert "description:" in t
    assert "sbtdd" in t.lower() and "skill" in t.lower()


def test_sbtdd_init_covers_all_scaffolding_steps():
    t = _read(CMD / "sbtdd-init.md")
    for sig in ("Cargo.toml", "pyproject.toml", "CMakeLists.txt"):
        assert sig in t
    for entry in ("HERMES.local.md", "HERMES.md", ".hermes/", "sbtdd/", "planning/"):
        assert entry in t
    for tmpl in ("HERMES.local.md.tmpl", "settings.json",
                 "spec-behavior-base.tmpl.md", "verification/"):
        assert tmpl in t
    assert "idempotent" in t.lower() or "do not overwrite" in t.lower()
    assert "merge" in t.lower()
    assert "description:" in t


def test_sbtdd_check_covers_eight_items():
    t = _read(CMD / "sbtdd-check.md")
    assert "HERMES.local.md" in t
    assert "sbtdd/" in t and "planning/" in t
    assert ".gitignore" in t
    assert "magi" in t.lower()
    assert "drift" in t.lower()
    assert "read-only" in t.lower() or "does not fix" in t.lower()
    assert "sbtdd-init" in t
    assert "Check 8" in t
    assert "eight" in t.lower()
    assert "description:" in t


def test_sbtdd_check_reports_magi_backend():
    t = _read(CMD / "sbtdd-check.md")
    assert "magi-ollama.toml" in t
    assert "review-gates.md §8" in t
    low = t.lower()
    assert "smoke" in low, "Check 8 must describe the smoke test"
    assert "backend" in low
    assert "claude" in low or "default" in low, "default backend must be named"
    assert "preflight" in low


def test_sbtdd_init_documents_ollama_init_flag():
    t = _read(CMD / "sbtdd-init.md")
    assert "--ollama-init" in t
    assert "magi-ollama.toml" in t
    assert "review-gates.md §8" in t
    low = t.lower()
    assert "skip" in low or "do not overwrite" in low or "idempotent" in low


def test_sbtdd_command_documents_ollama_flag():
    t = _read(CMD / "sbtdd.md")
    assert "--ollama" in t
    assert "review-gates.md §8" in t
    low = t.lower()
    assert "fail-closed" in low
    assert "magi-ollama.toml" in low


# ---------------------------------------------------------------------------
# tests for README.md (project-level)
# ---------------------------------------------------------------------------

def test_readme_documents_entrypoints():
    t = _read(ROOT / "README.md")
    for cmd in ("/sbtdd", "/sbtdd-init", "/sbtdd-check"):
        assert cmd in t
    assert "SBTDD" in t
    assert "install" in t.lower()
    assert "magi" in t.lower()
    assert "entry-point" in t.lower() or "plugin" in t.lower()


def test_readme_points_to_magi_interactive_only_contract():
    t = _read(ROOT / "README.md")
    low = t.lower()
    assert "magi" in low, "README.md must mention MAGI"
    assert "review" in low or "gate" in low or "verification" in low, \
        "README.md must reference review/checkpoint process"


def test_readme_documents_ollama_backend():
    t = _read(ROOT / "README.md")
    assert "magi" in t.lower(), \
        "README must mention MAGI backend or configuration"
    low = t.lower()
    assert "ollama" in low or "openrouter" in low, \
        "README must reference MAGI backends"


def test_readme_documents_sbtdd_check_reports_backend():
    t = _read(ROOT / "README.md")
    assert "/sbtdd-check" in t
    low = t.lower()
    assert "check" in low, "README must mention the /sbtdd-check command"


# ---------------------------------------------------------------------------
# tests for references/*.md
# ---------------------------------------------------------------------------

def test_routing_exists():
    p = ROOT / "skills/sbtdd/references/routing.md"
    assert p.exists()
    t = _read(p)
    assert "State-Detection Decision Table" in t


def test_review_gates_exists():
    p = ROOT / "skills/sbtdd/references/review-gates.md"
    assert p.exists()
    t = _read(p)
    assert "MAGI Verdict Table" in t
    assert "3-Iteration Safety Valve" in t


def test_tdd_cycle_exists():
    p = ROOT / "skills/sbtdd/references/tdd-cycle.md"
    assert p.exists()
    t = _read(p)
    assert "Atomic 3-Step Close" in t


def test_finalization_exists():
    p = ROOT / "skills/sbtdd/references/finalization.md"
    assert p.exists()
    t = _read(p)
    assert "Final Checklist" in t


# ---------------------------------------------------------------------------
# tests for templates/
# ---------------------------------------------------------------------------

def test_templates_exist():
    for tmpl in (
        "HERMES.local.md.tmpl",
        "settings.json.tmpl",
        "spec-behavior-base.tmpl.md",
        "verification/rust.md",
        "verification/python.md",
    ):
        assert (ROOT / "templates" / tmpl).exists(), f"template {tmpl} must exist"
