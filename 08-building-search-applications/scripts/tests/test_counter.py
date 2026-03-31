"""Unit tests for the thread-safe Counter class used across the pipeline scripts.

The Counter appears in transcript_enrich_summaries.py and
transcript_enrich_speaker.py.  We test it via the summaries module fixture
since it is the simplest to load.  Thread-safety is verified by running many
concurrent increments and checking the final value.
"""

import threading

import pytest


class TestCounter:
    def test_initial_value_is_zero(self, summaries_module):
        c = summaries_module.Counter()
        assert c.value == 0

    def test_single_increment_returns_new_value(self, summaries_module):
        c = summaries_module.Counter()
        result = c.increment()
        assert result == 1

    def test_multiple_increments_accumulate(self, summaries_module):
        c = summaries_module.Counter()
        c.increment()
        c.increment()
        val = c.increment()
        assert val == 3
        assert c.value == 3

    def test_value_attribute_reflects_increments(self, summaries_module):
        c = summaries_module.Counter()
        for _ in range(5):
            c.increment()
        assert c.value == 5

    def test_thread_safety_under_concurrent_increments(self, summaries_module):
        """Fire N threads each incrementing M times; final value must be N*M."""
        N_THREADS = 20
        INCREMENTS_PER_THREAD = 50

        c = summaries_module.Counter()

        def worker():
            for _ in range(INCREMENTS_PER_THREAD):
                c.increment()

        threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert c.value == N_THREADS * INCREMENTS_PER_THREAD

    def test_counters_are_independent(self, summaries_module):
        c1 = summaries_module.Counter()
        c2 = summaries_module.Counter()
        c1.increment()
        c1.increment()
        c2.increment()
        assert c1.value == 2
        assert c2.value == 1
