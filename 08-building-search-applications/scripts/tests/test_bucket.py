"""Unit tests for pure utility functions in transcript_enrich_bucket.py.

The module is loaded once per test session via the ``bucket_module`` fixture
defined in conftest.py.  All external dependencies and file I/O are mocked
at import time, so no network access or real files are required.
"""

import pytest


# ── clean_text ─────────────────────────────────────────────────────────────────


class TestCleanText:
    def test_replaces_newline_with_space(self, bucket_module):
        assert bucket_module.clean_text("Hello\nWorld") == "Hello World"

    def test_replaces_html_apostrophe_entity(self, bucket_module):
        assert bucket_module.clean_text("it&#39;s") == "it's"

    def test_removes_double_chevrons(self, bucket_module):
        assert bucket_module.clean_text(">>Speaker:") == "Speaker:"

    def test_collapses_double_spaces(self, bucket_module):
        assert bucket_module.clean_text("Hello  World") == "Hello World"

    def test_removes_inaudible_tag(self, bucket_module):
        assert bucket_module.clean_text("[inaudible] yes") == " yes"

    def test_leaves_clean_text_unchanged(self, bucket_module):
        text = "Hello World, this is a normal sentence."
        assert bucket_module.clean_text(text) == text

    def test_combined_cleanup(self, bucket_module):
        # Each replacement is applied once in order; removing [inaudible] can
        # reintroduce adjacent spaces, so we only assert the tags are gone.
        raw = ">>Hello\n[inaudible]  World"
        result = bucket_module.clean_text(raw)
        assert ">>" not in result
        assert "\n" not in result
        assert "[inaudible]" not in result

    def test_empty_string_returns_empty(self, bucket_module):
        assert bucket_module.clean_text("") == ""


# ── gen_metadata_master ────────────────────────────────────────────────────────


class TestGenMetadataMaster:
    def test_always_sets_start_to_midnight(self, bucket_module):
        meta = {"title": "T", "description": "D"}
        bucket_module.gen_metadata_master(meta)
        assert meta["start"] == "00:00:00"

    def test_concatenates_title_and_description(self, bucket_module):
        meta = {"title": "Hello", "description": "World"}
        bucket_module.gen_metadata_master(meta)
        assert meta["text"] == "Hello World"

    def test_uses_fallback_when_text_is_blank(self, bucket_module):
        meta = {"title": "   ", "description": "   "}
        bucket_module.gen_metadata_master(meta)
        assert meta["text"] == "No description available."

    def test_removes_newlines_from_combined_text(self, bucket_module):
        meta = {"title": "Hello\nWorld", "description": ""}
        bucket_module.gen_metadata_master(meta)
        assert "\n" not in meta["text"]

    def test_strips_surrounding_whitespace(self, bucket_module):
        meta = {"title": "  Hi  ", "description": ""}
        bucket_module.gen_metadata_master(meta)
        assert meta["text"] == meta["text"].strip()

    def test_only_description_present(self, bucket_module):
        meta = {"title": "", "description": "Just a description"}
        bucket_module.gen_metadata_master(meta)
        assert "Just a description" in meta["text"]


# ── VttSegment ─────────────────────────────────────────────────────────────────


class TestVttSegment:
    def test_constructs_from_complete_dict(self, bucket_module):
        seg = bucket_module.VttSegment({"text": "hello", "start": 1.5, "duration": 2.0})
        assert seg.text == "hello"
        assert seg.start == 1.5
        assert seg.duration == 2.0

    def test_missing_keys_default_to_none(self, bucket_module):
        seg = bucket_module.VttSegment({})
        assert seg.text is None
        assert seg.start is None
        assert seg.duration is None

    def test_partial_dict_sets_missing_fields_to_none(self, bucket_module):
        seg = bucket_module.VttSegment({"text": "only text"})
        assert seg.text == "only text"
        assert seg.start is None
        assert seg.duration is None

    def test_zero_start_is_not_none(self, bucket_module):
        seg = bucket_module.VttSegment({"text": "intro", "start": 0.0, "duration": 5.0})
        assert seg.start == 0.0


# ── append_text_to_previous_segment ───────────────────────────────────────────


class TestAppendTextToPreviousSegment:
    def test_appends_5pct_of_words_to_last_segment(self, bucket_module):
        # 20 words * PERCENTAGE_OVERLAP(0.05) = 1 word → appends words[0]
        twenty_words = " ".join(f"word{i}" for i in range(20))
        bucket_module.segments = [{"text": "base "}]
        bucket_module.append_text_to_previous_segment(twenty_words)
        assert bucket_module.segments[-1]["text"] == "base word0"

    def test_does_nothing_when_segments_is_empty(self, bucket_module):
        bucket_module.segments = []
        bucket_module.append_text_to_previous_segment("some overlap text here and more")
        assert bucket_module.segments == []

    def test_does_nothing_for_empty_text(self, bucket_module):
        bucket_module.segments = [{"text": "existing "}]
        bucket_module.append_text_to_previous_segment("")
        # int(0 * 0.05) = 0 words → join(words[0:0]) = ""
        assert bucket_module.segments[-1]["text"] == "existing "

    def test_only_last_segment_is_modified(self, bucket_module):
        bucket_module.segments = [{"text": "first "}, {"text": "last "}]
        twenty_words = " ".join(f"w{i}" for i in range(20))
        bucket_module.append_text_to_previous_segment(twenty_words)
        assert bucket_module.segments[0]["text"] == "first "  # unchanged
        assert bucket_module.segments[1]["text"] == "last w0"  # modified


# ── add_new_segment ────────────────────────────────────────────────────────────


class TestAddNewSegment:
    def test_formats_seconds_as_hh_mm_ss(self, bucket_module):
        bucket_module.segments = []
        meta = {"videoId": "abc", "title": "T", "description": "D"}
        bucket_module.add_new_segment(meta, "segment text", 90)  # 90 s = 00:01:30
        assert bucket_module.segments[0]["start"] == "00:01:30"

    def test_stores_raw_seconds(self, bucket_module):
        bucket_module.segments = []
        meta = {"videoId": "abc", "title": "T", "description": "D"}
        bucket_module.add_new_segment(meta, "text", 3661)
        assert bucket_module.segments[0]["seconds"] == 3661

    def test_stores_text(self, bucket_module):
        bucket_module.segments = []
        meta = {"videoId": "abc", "title": "T", "description": "D"}
        bucket_module.add_new_segment(meta, "hello world", 0)
        assert bucket_module.segments[0]["text"] == "hello world"

    def test_appended_segment_is_a_copy(self, bucket_module):
        # Mutating the returned segment should not affect the original dict
        bucket_module.segments = []
        meta = {"videoId": "original", "title": "T", "description": "D"}
        bucket_module.add_new_segment(meta, "text", 0)
        bucket_module.segments[0]["videoId"] = "mutated"
        assert meta["videoId"] == "original"

    def test_zero_seconds_formats_as_midnight(self, bucket_module):
        bucket_module.segments = []
        meta = {"videoId": "abc", "title": "T", "description": "D"}
        bucket_module.add_new_segment(meta, "intro", 0)
        assert bucket_module.segments[0]["start"] == "00:00:00"
