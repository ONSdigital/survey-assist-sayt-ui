"""Browser tests for authenticated session handling."""

from playwright.sync_api import Page

from .pages.home import HomePage
from .pages.login import LoginPage
from .pages.quick_test import QuickTestPage


def test_signed_in_session_survives_reload(
    authenticated_page: Page, credentials: tuple[str, str]
) -> None:
    """Keep the session after reload."""
    username, _ = credentials
    home = HomePage(authenticated_page)
    home.expect_signed_in(username)
    authenticated_page.reload()
    home.expect_signed_in(username)


def test_logout_blocks_protected_pages(authenticated_page: Page) -> None:
    """Verify protected pages are blocked after logout."""
    home = HomePage(authenticated_page)
    home.sign_out()
    login = LoginPage(authenticated_page)
    login.expect_open()

    authenticated_page.goto(QuickTestPage.PATH)
    login.expect_open()
