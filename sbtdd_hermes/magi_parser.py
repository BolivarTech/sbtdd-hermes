import multiprocessing
import re
from typing import Callable

from ._config import MAGI_PARSE_TIMEOUT, MAGI_BANNER_RE, MAGI_VEREDICTO_RE, MAGI_FINDING_RE


class ParseError(RuntimeError):
    pass


def _do_parse(report: str) -> dict:
    if "+==================================================+" not in report:
        raise ParseError("Missing MAGI banner")
    if "CONSENSUS:" not in report:
        raise ParseError("Missing consensus section")

    verdict_match = re.search(MAGI_VEREDICTO_RE, report)
    if not verdict_match:
        raise ParseError("Could not extract verdict")
    
    # Strip trailing vote counts like "(3-0)"
    raw_verdict = verdict_match.group(1).strip()
    verdict = re.sub(r"\s*\(\d+-\d+\)\s*$", "", raw_verdict)
    
    findings = []
    for line in report.splitlines():
        m = re.match(MAGI_FINDING_RE, line)
        if m:
            findings.append({"severity": m.group(2), "title": m.group(3)})

    return {
        "veredicto": verdict,
        "findings": findings,
        "format_version": "2.0",
        "parse_confidence": 1.0 if findings else 0.5,
    }


def _queue_wrapper(queue, func, args):
    try:
        result = func(*args)
        queue.put(("ok", result))
    except Exception as e:
        queue.put(("error", e))


def run_with_regex_timeout(func: Callable, func_args: tuple, timeout: float = MAGI_PARSE_TIMEOUT):
    result_queue = multiprocessing.Queue()

    p = multiprocessing.Process(target=_queue_wrapper, args=(result_queue, func, func_args))
    p.start()
    p.join(timeout=timeout)

    if p.is_alive():
        p.terminate()
        p.join(timeout=1.0)
        raise TimeoutError(f"MAGI parsing exceeded {timeout}s")

    try:
        status, payload = result_queue.get(timeout=1.0)
    except Exception:
        raise ParseError("MAGI parsing failed: worker terminated before producing result")

    if status == "error":
        raise payload
    return payload


def parse_magi_report(report: str) -> dict:
    try:
        return run_with_regex_timeout(_do_parse, (report,), timeout=MAGI_PARSE_TIMEOUT)
    except TimeoutError:
        raise ParseError("MAGI parsing timeout")
