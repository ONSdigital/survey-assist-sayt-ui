"""Sign-in page interactions."""

import re

from playwright.sync_api import Page, expect


class LoginPage:
    """Provide interactions with the sign-in page."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url
        self.email = page.get_by_label("Email address")
        self.password = page.get_by_label("Password", exact=True)
        self.login_button = page.get_by_role("button", name="Login")

    def open(self) -> None:
        """Request the home page and verify its redirect to sign-in."""
        self.page.goto(f"{self.base_url}/")
        self.expect_open()

    def expect_open(self) -> None:
        """Verify the sign-in page is open."""
        expect(self.page).to_have_url(re.compile(r"/login$"))
        expect(self.login_button).to_be_visible()

    def sign_in(self, username: str, password: str) -> None:
        """Sign in with the supplied credentials."""
        self.email.fill(username)
        self.password.fill(password)
        self.login_button.click()
