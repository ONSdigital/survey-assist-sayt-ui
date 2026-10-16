"""Authenticated home page interactions."""

import re

from playwright.sync_api import Page, expect


class HomePage:
    """Provide interactions with the authenticated home page."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url
        self.quick_test_button = page.get_by_role("button", name="SAYT Quick Test")
        self.sign_out_button = page.get_by_role("button", name="Sign out")

    def expect_signed_in(self, username: str) -> None:
        """Verify the home page shows the signed-in user."""
        expect(self.page).to_have_url(f"{self.base_url}/")
        expect(
            self.page.get_by_text(f"You are signed in as {username.strip().lower()}.", exact=True)
        ).to_be_visible()

    def open_quick_test(self) -> None:
        """Open the SAYT Quick Test page."""
        self.quick_test_button.click()
        expect(self.page).to_have_url(re.compile(r"/api-autosuggest$"))

    def sign_out(self) -> None:
        """Sign out from the home page."""
        self.sign_out_button.click()
