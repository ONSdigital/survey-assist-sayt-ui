"""SAYT Quick Test page interactions."""

from playwright.sync_api import Page, expect


class QuickTestPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.activity = page.get_by_role("combobox")
        self.suggestions = page.get_by_role("listbox", name="Suggested industries")
        self.not_listed = page.get_by_label("Not listed")
        self.description = page.get_by_label("Describe the main activity of your organisation")
        self.save_button = page.get_by_role("button", name="Save and continue")

    def select_first_suggestion(self, search_term: str) -> str:
        self.activity.fill(search_term)
        suggestion = self.suggestions.get_by_role("option").first
        expect(suggestion).to_be_visible()
        selected_activity = suggestion.inner_text()
        suggestion.click()
        expect(self.activity).to_have_value(selected_activity)
        return selected_activity

    def select_not_listed(self, description: str) -> None:
        self.not_listed.check()
        expect(self.activity).to_be_disabled()
        self.description.fill(description)

    def save(self, selected_activity: str) -> None:
        self.save_button.click()
        expect(
            self.page.get_by_text(
                f'Your response "{selected_activity}" has been saved successfully.'
            )
        ).to_be_visible()
