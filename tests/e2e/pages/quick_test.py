"""SAYT Quick Test page interactions."""

from playwright.sync_api import Page, expect


class QuickTestPage:
    """Provide interactions with the SAYT Quick Test page."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.activity = page.get_by_role("combobox")
        self.suggestions = page.get_by_role("listbox", name="Suggested industries")
        self.not_listed = page.get_by_label("Not listed")
        self.description = page.get_by_label("Describe the main activity of your organisation")
        self.save_button = page.get_by_role("button", name="Save and continue")

    def expect_loaded(self) -> None:
        """Verify that the autosuggest input is ready."""
        expect(self.activity).to_be_visible()

    def search_and_select_expected_suggestion(
        self, search_term: str, expected_industry: str
    ) -> None:
        """Select the suggestion that matches the expected industry for the search term."""
        self.activity.fill(search_term)
        suggestion = self.suggestions.get_by_role("option", name=expected_industry, exact=True)
        expect(suggestion).to_be_visible()
        suggestion.click()

    def select_not_listed(self, description: str) -> None:
        """Select Not listed and enter a description."""
        self.not_listed.check()
        expect(self.activity).to_be_disabled()
        self.description.fill(description)

    def save(self) -> None:
        """Save the response."""
        self.save_button.click()

    def expect_saved(self, selected_activity: str) -> None:
        """Verify the response confirmation."""
        expect(
            self.page.get_by_text(
                f'Your response "{selected_activity}" has been saved successfully.'
            )
        ).to_be_visible()
