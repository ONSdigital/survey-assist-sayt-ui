"""Configuration for browser tests against a deployed UI."""

import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pages.home import HomePage
from pages.login import LoginPage
from playwright.sync_api import Page
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
    """Return the user credentials used for authentication."""
    username = os.environ.get("SAYT_E2E_USERNAME")
    password = os.environ.get("SAYT_E2E_PASSWORD")
    if not username or not password:
        raise pytest.UsageError("Set SAYT_E2E_USERNAME and SAYT_E2E_PASSWORD.")
    return username, password


@pytest.fixture
def authenticated_page(page: Page, base_url: str, credentials: tuple[str, str]) -> Page:
    """Sign in with a fresh browser context."""
    username, password = credentials
    login = LoginPage(page, base_url)
    login.open()
    login.sign_in(username, password)
    HomePage(page, base_url).expect_signed_in(username)
    return page
