"""Configuration for browser tests against a deployed UI."""

from collections.abc import Iterator
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from playwright.sync_api import BrowserContext, Page
import pytest

from .assets import AssetMonitor
from .pages.home import HomePage
from .pages.login import LoginPage

load_dotenv()


@pytest.fixture(autouse=True)
def configured_context_timeout(context: BrowserContext) -> None:
    """Set the default timeout for each browser test."""
    context.set_default_timeout(10_000)


@pytest.fixture(autouse=True)
def warn_page_asset_failures(page: Page) -> Iterator[None]:
    """Report asset failures for each browser test."""
    monitor = AssetMonitor(page)
    page.on("response", monitor.on_response)
    page.on("requestfailed", monitor.on_request_failed)
    yield
    monitor.warn_if_failed()


@pytest.fixture(scope="session")
def connect_options() -> dict[str, str] | None:
    """Connect the browser fixture to the Playwright server."""
    ws_endpoint = os.environ.get("PLAYWRIGHT_WS_ENDPOINT")
    if not ws_endpoint:
        return None
    return {"endpoint": ws_endpoint, "expose_network": "<loopback>"}


@pytest.fixture(scope="session", name="base_url")
def configured_base_url() -> str:
    """Return the URL of the deployed UI."""
    url = os.environ.get("TEST_E2E_BASE_URL", "").strip().rstrip("/")
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in ("https", "http") or not parsed_url.netloc:
        raise pytest.UsageError("Set TEST_E2E_BASE_URL to the UI's full http(s) URL.")
    return url


@pytest.fixture(name="credentials")
def configured_credentials() -> tuple[str, str]:
    """Return the user credentials used for authentication."""
    username = os.environ.get("TEST_E2E_USERNAME")
    password = os.environ.get("TEST_E2E_PASSWORD")
    if not username or not password:
        raise pytest.UsageError("Set TEST_E2E_USERNAME and TEST_E2E_PASSWORD.")
    return username, password


@pytest.fixture(scope="session", name="browser_type_launch_args")
def configured_browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    """Disable QUIC to standardise traffic flow across different environments."""
    return {
        **browser_type_launch_args,
        "args": [*browser_type_launch_args.get("args", []), "--disable-quic"],
    }


@pytest.fixture
def authenticated_page(page: Page, base_url: str, credentials: tuple[str, str]) -> Page:
    """Sign in with a fresh browser context."""
    username, password = credentials
    login = LoginPage(page, base_url)
    login.open()
    login.sign_in(username, password)
    HomePage(page, base_url).expect_signed_in(username)
    return page
