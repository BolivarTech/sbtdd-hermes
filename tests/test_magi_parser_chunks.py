"""
TDD RED: MAGI parser robustness — fragmented chunks + fallback parsing.
Must fail before implementation.
"""

import pytest
from sbtdd_hermes.magi_parser import parse_magi_report, ParseError


class TestMagiParserChunkRobustness:
    """MAGI parser must handle fragmented / malformed report input."""

    def test_verdict_split_across_lines(self):
        """Verdict line broken across chunks should still parse."""
        report = (
            "+==================================================+\n"
            "|              MAGI SYSTEM -- VERDICT              |\n"
            "+==================================================+\n"
            "|  CONSENSUS:\n"
            "    GO WITH CAVEATS (3-0)                          |\n"
            "+==================================================+\n"
        )
        result = parse_magi_report(report)
        assert "GO WITH CAVEATS" in result["veredicto"]

    def test_fallback_without_banner(self):
        """If banner missing but CONSENSUS present, should still extract verdict."""
        report = (
            "Some preamble text\n"
            "|  CONSENSUS: GO                                   |\n"
            "More text here\n"
        )
        result = parse_magi_report(report)
        assert result["veredicto"] == "GO"

    def test_no_consensus_raises_parse_error(self):
        """Without CONSENSUS keyword, should raise ParseError."""
        report = "Some random text without any verdict"
        with pytest.raises(ParseError):
            parse_magi_report(report)
