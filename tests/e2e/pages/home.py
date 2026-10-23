"""Authenticated home page interactions."""

from playwright.sync_api import Page, expect

from .cognitive_survey import CognitiveSurveyPage


class HomePage:
    """Provide interactions with the authenticated home page."""

    PATH = "/"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.quick_test_button = page.get_by_role("button", name="SAYT Quick Test")
        self.cognitive_test_button = page.get_by_role("button", name="Cognitive Test")
        self.sign_out_button = page.get_by_role("button", name="Sign out")

    def expect_signed_in(self, username: str) -> None:
        """Verify the home page shows the signed-in user."""
        expect(self.page).to_have_url(self.PATH)
        expect(
            self.page.get_by_text(f"You are signed in as {username.strip().lower()}.", exact=True)
        ).to_be_visible()

    def open_quick_test(self) -> None:
        """Open the SAYT Quick Test page."""
        self.quick_test_button.click()

    def open_cognitive_test(self) -> None:
        """Open the cognitive survey from the home page."""
        self.cognitive_test_button.click()
        expect(self.page).to_have_url(f"{CognitiveSurveyPage.PATH}/questions/q1")

    def sign_out(self) -> None:
        """Sign out from the home page."""
        self.sign_out_button.click()
