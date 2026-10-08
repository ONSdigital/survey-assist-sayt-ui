"""Configuration for browser tests against a deployed UI."""

import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
import pytest

load_dotenv()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the URL of the deployed UI."""
    url = os.environ.get("SAYT_E2E_BASE_URL", "").strip().rstrip("/")
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in ("https", "http") or not parsed_url.netloc:
        raise pytest.UsageError("Set SAYT_E2E_BASE_URL to the UI's full http(s) URL.")
    return url


@pytest.fixture
def credentials() -> tuple[str, str]:
    """Return the dedicated sandbox test account credentials."""
    username = os.environ.get("SAYT_E2E_USERNAME")
    password = os.environ.get("SAYT_E2E_PASSWORD")
    if not username or not password:
        raise pytest.UsageError("Set SAYT_E2E_USERNAME and SAYT_E2E_PASSWORD.")
    return username, password
