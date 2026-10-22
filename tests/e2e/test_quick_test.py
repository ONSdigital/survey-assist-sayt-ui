"""Browser tests for SAYT Quick Test selections."""

from playwright.sync_api import Page, expect
import pytest

from .pages.home import HomePage
from .pages.quick_test import QuickTestPage


@pytest.mark.parametrize(
    ("search_term", "expected_industry"),
    [
        ("farmer", "Sheep farming: 01450"),
        ("consultant creating websites for clients", "Website design and development: 62012"),
    ],
)
def test_select_expected_activity_and_save(
    authenticated_page: Page, search_term: str, expected_industry: str
) -> None:
    """Search for, select, and save the expected suggestion from SAYT results."""
    HomePage(authenticated_page).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    quick_test.expect_loaded()
    quick_test.search_and_select_expected_suggestion(search_term, expected_industry)
    quick_test.save()
    quick_test.expect_saved(expected_industry)


def test_suggestions_change_as_search_term_changes(authenticated_page: Page) -> None:
    """Verify that live suggestions change as the user types and deletes text."""
    HomePage(authenticated_page).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    quick_test.expect_loaded()
    options = quick_test.suggestions.get_by_role("option")

    # Type "farm" into the activity input and check initial suggestions
    quick_test.activity.press_sequentially("farm")
    expect(quick_test.activity).to_have_value("farm")
    expect(options.nth(1)).to_be_visible()
    initial_suggestions = options.all_inner_texts()

    # Further refine the search term to "farming sheep" and check suggestions have updated
    quick_test.activity.press_sequentially("ing sheep")
    expect(quick_test.activity).to_have_value("farming sheep")
    expect(options.nth(1)).to_be_visible()
    expect(options).not_to_have_text(initial_suggestions)
    refined_suggestions = options.all_inner_texts()

    # Delete characters until only "farming" remains, check suggestions have changed
    for _ in range(6):
        quick_test.activity.press("Backspace")
    expect(quick_test.activity).to_have_value("farming")
    expect(options.nth(1)).to_be_visible()
    expect(options).not_to_have_text(refined_suggestions)


def test_select_activity_not_listed_and_save(authenticated_page: Page) -> None:
    """Save a self-described description when no suggestion is selected."""
    HomePage(authenticated_page).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    quick_test.expect_loaded()
    description = "Independent game design"
    quick_test.select_not_listed(description)
    quick_test.save()
    quick_test.expect_saved(description)
