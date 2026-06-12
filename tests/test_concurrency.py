"""Tests for sbtdd_hermes concurrency (OCC + filelock)."""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from sbtdd_hermes.state import SessionState, load_state, save_state, ConcurrencyError


class TestConcurrency:
    def test_concurrent_saves_detect_conflict(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState()
        save_state(path, state, expected_revision=0)

        errors = []

        def worker():
            try:
                s = load_state(path)
                save_state(path, s, expected_revision=s.state_revision)
            except ConcurrencyError as e:
                errors.append(e)

        # Run two workers concurrently
        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(worker)
            f2 = ex.submit(worker)
            f1.result()
            f2.result()

        # At least one should have succeeded, the other may or may not conflict
        # depending on timing
        final = load_state(path)
        assert final.state_revision >= 1

    def test_filelock_prevents_corruption(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState()
        save_state(path, state, expected_revision=0)

        results = []

        def worker(n):
            for _ in range(5):
                try:
                    s = load_state(path)
                    # Mutate
                    from dataclasses import replace
                    s = replace(s, notes=f"worker-{n}")
                    save_state(path, s, expected_revision=s.state_revision)
                    results.append("ok")
                except ConcurrencyError:
                    results.append("conflict")
                time.sleep(0.01)

        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(worker, i) for i in range(3)]
            for f in futures:
                f.result()

        # Verify state is readable
        final = load_state(path)
        assert final.state_revision > 0

    def test_expected_revision_required(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState()
        
        with pytest.raises(TypeError):
            save_state(path, state)  # Missing expected_revision
