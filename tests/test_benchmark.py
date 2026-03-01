# pyright: reportUnusedImport=false
"""Tests for the LoCoMo benchmark runner.

Validates dataset loading, the ``simple_match`` evaluation function,
the BenchmarkSuite aggregation logic, and a quick offline run of the
built-in mini dataset (which uses the in-memory degraded engine).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run import (  # noqa: E402
    LOCOMO_MINI,
    BenchmarkResult,
    BenchmarkSuite,
    load_dataset,
    simple_match,
)

# ───────────────────────────────────────────────────────────────────
# simple_match
# ───────────────────────────────────────────────────────────────────


class TestSimpleMatch:
    def test_exact(self):
        assert simple_match("Google", "Google")

    def test_case_insensitive(self):
        assert simple_match("google", "Google")

    def test_substring(self):
        assert simple_match("Alice works at Google", "Google")

    def test_mismatch(self):
        assert not simple_match("Meta", "Google")

    def test_empty_predicted(self):
        assert not simple_match("", "Google")

    def test_whitespace_handling(self):
        assert simple_match("  Google  ", "Google")


# ───────────────────────────────────────────────────────────────────
# BenchmarkSuite
# ───────────────────────────────────────────────────────────────────


class TestBenchmarkSuite:
    def _make_suite(self, results: list[tuple[bool, str]]) -> BenchmarkSuite:
        suite = BenchmarkSuite(name="test")
        for i, (correct, cat) in enumerate(results):
            suite.results.append(
                BenchmarkResult(
                    question_id=f"q{i}",
                    predicted="pred",
                    expected="exp",
                    correct=correct,
                    latency_ms=10.0,
                    category=cat,
                )
            )
        return suite

    def test_accuracy_full(self):
        suite = self._make_suite([(True, "a"), (True, "a")])
        assert suite.accuracy == 100.0

    def test_accuracy_half(self):
        suite = self._make_suite([(True, "a"), (False, "a")])
        assert suite.accuracy == 50.0

    def test_accuracy_empty(self):
        suite = BenchmarkSuite(name="empty")
        assert suite.accuracy == 0.0

    def test_accuracy_by_category(self):
        suite = self._make_suite([
            (True, "temporal"),
            (False, "temporal"),
            (True, "factual"),
            (True, "factual"),
        ])
        cats = suite.accuracy_by_category()
        assert cats["temporal"] == 50.0
        assert cats["factual"] == 100.0

    def test_mean_latency(self):
        suite = self._make_suite([(True, "a")])
        assert suite.mean_latency_ms == 10.0


# ───────────────────────────────────────────────────────────────────
# Dataset loading
# ───────────────────────────────────────────────────────────────────


class TestDataset:
    def test_builtin_mini_not_empty(self):
        assert len(LOCOMO_MINI) >= 6

    def test_load_default(self):
        data = load_dataset(None)
        assert data is LOCOMO_MINI

    def test_load_missing_file(self):
        data = load_dataset("/nonexistent/path.json")
        assert data is LOCOMO_MINI

    def test_all_questions_have_required_keys(self):
        for item in LOCOMO_MINI:
            assert "id" in item
            assert "question" in item
            assert "answer" in item
            assert "episodes" in item
            assert len(item["episodes"]) > 0

    def test_categories_present(self):
        cats = {item["category"] for item in LOCOMO_MINI}
        assert "temporal" in cats
        assert "factual" in cats
        assert "multi-hop" in cats


# ───────────────────────────────────────────────────────────────────
# Offline benchmark run
# ───────────────────────────────────────────────────────────────────


class TestBenchmarkRun:
    @pytest.mark.asyncio
    async def test_offline_run(self):
        """Run the benchmark against the in-memory degraded engine.

        All answers will be empty (engine returns []) → all incorrect,
        but the run should complete without errors.
        """
        from benchmarks.run import run_benchmark

        suite = await run_benchmark(LOCOMO_MINI)
        assert suite.total == len(LOCOMO_MINI)
        # In degraded mode every prediction is "" → 0% accuracy
        assert suite.accuracy == 0.0
        assert suite.mean_latency_ms >= 0
