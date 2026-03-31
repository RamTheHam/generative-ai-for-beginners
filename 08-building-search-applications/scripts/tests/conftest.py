"""Pytest configuration for 08-building-search-applications/scripts tests.

All heavy external dependencies (openai, tiktoken, rich, tenacity, etc.) are
pre-mocked in sys.modules so the scripts can be imported without those packages
being installed.  Module-level side-effects (argparse exits, file I/O,
threading) are patched away inside load_script().
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

# ── 1. Pre-populate sys.modules with lightweight mocks ────────────────────────
# This runs when conftest.py is first imported (before test collection), so all
# subsequent `from X import Y` statements inside the scripts resolve to mocks.


def _passthrough(*args, **kwargs):
    """Decorator factory that returns the decorated function unchanged."""
    return lambda fn: fn


_tenacity = MagicMock()
_tenacity.retry = _passthrough
_tenacity.wait_random_exponential = _passthrough
_tenacity.stop_after_attempt = _passthrough
_tenacity.retry_if_not_exception_type = _passthrough

_tokenizer = MagicMock()
_tokenizer.encode.return_value = list(range(10))  # 10 fake tokens

_tiktoken = MagicMock()
_tiktoken.encoding_for_model.return_value = _tokenizer
_tiktoken.get_encoding.return_value = _tokenizer

_MOCK_MODULES: dict = {
    "tiktoken": _tiktoken,
    "openai": MagicMock(),
    "openai.embeddings_utils": MagicMock(),
    "dotenv": MagicMock(),
    "rich": MagicMock(),
    "rich.progress": MagicMock(),
    "tenacity": _tenacity,
    "googleapiclient": MagicMock(),
    "googleapiclient.discovery": MagicMock(),
    "googleapiclient.errors": MagicMock(),
    "youtube_transcript_api": MagicMock(),
    "youtube_transcript_api.formatters": MagicMock(),
}

for _name, _mock in _MOCK_MODULES.items():
    sys.modules.setdefault(_name, _mock)

# ── 2. load_script helper ─────────────────────────────────────────────────────

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ENV = {
    "AZURE_OPENAI_API_KEY": "test-key",
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
    "GOOGLE_DEVELOPER_API_KEY": "test-google-key",
    "AZURE_OPENAI_MODEL_DEPLOYMENT_NAME": "gpt-35-turbo",
}


def load_script(name: str) -> object:
    """Import *name*.py from SCRIPTS_DIR with all module-level side-effects mocked.

    Specifically:
    - sys.argv is set to ``['script.py', '-f', '/tmp/test_transcripts']``
    - Required environment variables are injected
    - ``glob.glob`` returns an empty list (no files to process)
    - ``builtins.open`` returns a mock whose ``.read()`` yields ``'[]'``
      so that ``json.load(f)`` produces an empty list everywhere
    """
    sys.modules.pop(name, None)

    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)

    with (
        patch.object(sys, "argv", ["script.py", "-f", "/tmp/test_transcripts"]),
        patch.dict(os.environ, _ENV),
        patch("glob.glob", return_value=[]),
        patch("builtins.open", mock_open(read_data="[]")),
    ):
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(SCRIPTS_DIR, f"{name}.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)

    return mod


# ── 3. Module-scoped fixtures (one per script under test) ─────────────────────


@pytest.fixture(scope="module")
def bucket_module():
    return load_script("transcript_enrich_bucket")


@pytest.fixture(scope="module")
def embeddings_module():
    return load_script("transcript_enrich_embeddings")


@pytest.fixture(scope="module")
def lite_module():
    return load_script("transcript_enrich_lite")


@pytest.fixture(scope="module")
def summaries_module():
    return load_script("transcript_enrich_summaries")
