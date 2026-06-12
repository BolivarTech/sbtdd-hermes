"""Tests for sbtdd_hermes.magi_parser module."""

import pytest
from sbtdd_hermes.magi_parser import parse_magi_report, ParseError


SAMPLE_MAGI_REPORT = """
+==================================================+
|              MAGI SYSTEM -- VERDICT              |
+==================================================+
|  Melchior (Scientist):   CONDITIONAL (85%)       |
|  Balthasar (Pragmatist): CONDITIONAL (83%)       |
|  Caspar (Critic):        CONDITIONAL (78%)       |
+==================================================+
|  CONSENSUS: GO WITH CAVEATS (3-0)                |
+==================================================+

## Key Findings
[!!]  [WARNING]  Race condition in state updates
[!!!] [CRITICAL] Missing agent-writable state update
[i]   [INFO]     TDD-Guard heuristic appropriately scoped

## Conditions for Approval
- Condition 1: Add sbtdd_update_state tool
- Condition 2: Implement atomic write

## Recommended Actions
- Fix critical finding before implementation
"""


class TestParseMagiReport:
    def test_parse_valid_report(self):
        result = parse_magi_report(SAMPLE_MAGI_REPORT)
        assert result["veredicto"] == "GO WITH CAVEATS"
        assert result["format_version"] == "2.0"
        assert len(result["findings"]) >= 2  # At least WARNING and CRITICAL
        
        # Check findings
        severities = [f["severity"] for f in result["findings"]]
        assert "WARNING" in severities
        assert "CRITICAL" in severities

    def test_parse_missing_banner(self):
        with pytest.raises(ParseError, match="Missing MAGI banner"):
            parse_magi_report("random text without banner")

    def test_parse_missing_consensus(self):
        with pytest.raises(ParseError, match="Missing consensus section"):
            parse_magi_report("+==================================================+")

    def test_parse_empty_findings(self):
        report = """
+==================================================+
|              MAGI SYSTEM -- VERDICT              |
+==================================================+
|  CONSENSUS: GO (3-0)                             |
+==================================================+
"""
        result = parse_magi_report(report)
        assert result["veredicto"] == "GO"
        assert result["parse_confidence"] == 0.5  # No findings

    def test_timeout_on_malicious_input(self):
        # Very long string with many tokens to trigger ReDoS if regex were bad
        # Uses proper pipe-delimited MAGI format
        malicious = (
            "+==================================================+\n"
            "|  CONSENSUS: " + "A " * 10000 + "|\n"
            "+==================================================+"
        )
        # Should NOT timeout with our linear regexes
        result = parse_magi_report(malicious)
        # Veredicto will be "A A A ..." - just verify parsing succeeded
        assert result["veredicto"].startswith("A")
        assert result["format_version"] == "2.0"
