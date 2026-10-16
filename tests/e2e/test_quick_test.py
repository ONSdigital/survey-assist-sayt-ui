"""Browser tests for SAYT Quick Test selections."""

from playwright.sync_api import Page
import pytest

from .pages.home import HomePage
from .pages.quick_test import QuickTestPage


@pytest.mark.parametrize("search_term", ["game development", "cow farming"])
def test_select_suggested_activity_and_save(
    authenticated_page: Page, base_url: str, search_term: str
) -> None:
    """Search for, select, and save the first suggestion from SAYT results."""
    HomePage(authenticated_page, base_url).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    selected_activity = quick_test.select_first_suggestion(search_term)
    quick_test.save(selected_activity)


def test_select_activity_not_listed_and_save(authenticated_page: Page, base_url: str) -> None:
    """Save a self-described description when no suggestion is selected."""
    HomePage(authenticated_page, base_url).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    description = "Independent game design"
    quick_test.select_not_listed(description)
    quick_test.save(description)
