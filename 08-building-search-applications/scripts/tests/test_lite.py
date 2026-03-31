"""Unit tests for transcript_enrich_lite.py.

``remove_text`` strips the ``text`` and ``description`` fields from a list of
segment dicts, producing a lighter payload for the search index.
"""

import pytest


class TestRemoveText:
    def test_removes_text_field(self, lite_module):
        segments = [{"videoId": "abc", "text": "hello", "title": "T"}]
        result = lite_module.remove_text(segments)
        assert "text" not in result[0]

    def test_removes_description_field(self, lite_module):
        segments = [{"videoId": "abc", "description": "Some description", "title": "T"}]
        result = lite_module.remove_text(segments)
        assert "description" not in result[0]

    def test_preserves_all_other_fields(self, lite_module):
        segments = [
            {
                "videoId": "abc123",
                "title": "My Video",
                "start": "00:01:30",
                "seconds": 90,
                "text": "should be removed",
                "description": "also removed",
            }
        ]
        result = lite_module.remove_text(segments)
        assert result[0]["videoId"] == "abc123"
        assert result[0]["title"] == "My Video"
        assert result[0]["start"] == "00:01:30"
        assert result[0]["seconds"] == 90

    def test_empty_list_returns_empty_list(self, lite_module):
        assert lite_module.remove_text([]) == []

    def test_segment_without_text_or_description(self, lite_module):
        segments = [{"videoId": "abc", "title": "T"}]
        result = lite_module.remove_text(segments)
        assert result[0] == {"videoId": "abc", "title": "T"}

    def test_multiple_segments_all_stripped(self, lite_module):
        segments = [
            {"videoId": "v1", "text": "text1", "title": "T1"},
            {"videoId": "v2", "text": "text2", "title": "T2"},
        ]
        result = lite_module.remove_text(segments)
        assert len(result) == 2
        assert all("text" not in seg for seg in result)

    def test_returns_new_list_not_in_place(self, lite_module):
        original = [{"videoId": "abc", "text": "t", "title": "T"}]
        result = lite_module.remove_text(original)
        # Original should be unmodified
        assert "text" in original[0]
        assert result is not original
