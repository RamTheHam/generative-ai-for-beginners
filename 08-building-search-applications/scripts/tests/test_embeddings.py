"""Unit tests for pure utility functions in transcript_enrich_embeddings.py.

``normalize_text`` cleans raw transcript text before embedding.
``convert_time_to_seconds`` is used to sort output segments by time.
Both are pure functions with no external dependencies.
"""

import pytest


# ── normalize_text ─────────────────────────────────────────────────────────────


class TestNormalizeText:
    def test_collapses_multiple_spaces(self, embeddings_module):
        assert embeddings_module.normalize_text("Hello   World") == "Hello World"

    def test_strips_leading_and_trailing_whitespace(self, embeddings_module):
        assert embeddings_module.normalize_text("  hello  ") == "hello"

    def test_removes_period_comma_pattern(self, embeddings_module):
        # regex r". ," matches any-char + space + comma and removes it
        result = embeddings_module.normalize_text("Hello. , World")
        assert ". ," not in result

    def test_replaces_double_periods(self, embeddings_module):
        assert embeddings_module.normalize_text("end..start") == "end.start"

    def test_replaces_period_space_period(self, embeddings_module):
        assert embeddings_module.normalize_text("end. .start") == "end.start"

    def test_removes_newlines(self, embeddings_module):
        # \n is first converted to a space by the \s+ regex, so it disappears
        result = embeddings_module.normalize_text("line1\nline2")
        assert "\n" not in result

    def test_empty_string_returns_empty(self, embeddings_module):
        assert embeddings_module.normalize_text("") == ""

    def test_already_clean_text_is_unchanged(self, embeddings_module):
        text = "This is already clean text"
        assert embeddings_module.normalize_text(text) == text

    def test_tabs_are_treated_as_whitespace(self, embeddings_module):
        result = embeddings_module.normalize_text("word1\t\tword2")
        assert "\t" not in result
        assert result == "word1 word2"


# ── convert_time_to_seconds ────────────────────────────────────────────────────


class TestConvertTimeToSeconds:
    def test_converts_minutes_and_seconds(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("00:01:30") == 90

    def test_converts_hours_minutes_seconds(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("01:00:00") == 3600

    def test_converts_all_zeros(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("00:00:00") == 0

    def test_converts_large_timestamp(self, embeddings_module):
        # 1h 1m 1s = 3661s
        assert embeddings_module.convert_time_to_seconds("01:01:01") == 3661

    def test_returns_zero_for_invalid_format(self, embeddings_module):
        # Missing hour component → len != 3 → returns 0
        assert embeddings_module.convert_time_to_seconds("01:30") == 0

    def test_returns_zero_for_empty_string(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("") == 0

    def test_converts_seconds_only_timestamp(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("00:00:45") == 45

    def test_converts_max_minutes_in_hour(self, embeddings_module):
        assert embeddings_module.convert_time_to_seconds("00:59:59") == 3599
