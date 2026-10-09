"""Browser tests for authenticated session handling."""

from pages.home import HomePage
from pages.login import LoginPage
from playwright.sync_api import Page


def test_session_survives_reload_and_logout_blocks_protected_pages(
    page: Page, base_url: str, credentials: tuple[str, str]
) -> None:
    """Keep the session after navigation and deny access after sign-out."""
    username, password = credentials
    login = LoginPage(page, base_url)
    home = HomePage(page, base_url)

    login.open()
    login.sign_in(username, password)
    home.expect_signed_in(username)
    page.reload()
    home.expect_signed_in(username)

    home.sign_out()
    login.expect_open()
    page.goto(f"{base_url}/api-autosuggest")
    login.expect_open()
