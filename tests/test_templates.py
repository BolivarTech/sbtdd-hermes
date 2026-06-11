from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_settings_json_tmpl():
    p = ROOT / "templates/settings.json.tmpl"
    text = p.read_text(encoding="utf-8")
    data = __import__("json").loads(text)
    assert data["settings"]["enforce_tdd_discipline"] is True
    assert "phase_prefixes" in data["settings"]
    assert set(data["settings"]["phase_prefixes"].keys()) == {"red", "green", "refactor"}
    assert data["settings"]["auto_save_state"] is True


def test_hermes_local_md_tmpl_has_precedence_section():
    p = ROOT / "templates/HERMES.local.md.tmpl"
    text = p.read_text(encoding="utf-8")
    assert "HERMES.md" in text
    assert "precedence" in text.lower() or "prevails" in text.lower()


def test_spec_behavior_base_tmpl_has_scenario_placeholder():
    p = ROOT / "templates/spec-behavior-base.tmpl.md"
    text = p.read_text(encoding="utf-8")
    assert "Scenario:" in text
    assert "Given" in text and "When" in text and "Then" in text
    assert "Feature:" in text


def test_verification_rust_present():
    p = ROOT / "templates/verification/rust.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cargo nextest run" in text


def test_verification_python_present():
    p = ROOT / "templates/verification/python.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "pytest" in text


def test_verification_cpp_present():
    p = ROOT / "templates/verification/cpp.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cmake" in text.lower()
