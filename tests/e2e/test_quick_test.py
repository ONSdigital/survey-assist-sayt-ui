"""Browser tests for SAYT Quick Test selections."""

from playwright.sync_api import Page, expect
import pytest

from .pages.home import HomePage
from .pages.quick_test import QuickTestPage


@pytest.fixture(name="quick_test")
def opened_quick_test(authenticated_page: Page) -> QuickTestPage:
    """Open the SAYT Quick Test page from the authenticated home page."""
    HomePage(authenticated_page).open_quick_test()
    quick_test = QuickTestPage(authenticated_page)
    quick_test.expect_loaded()
    return quick_test


@pytest.mark.parametrize(
    ("search_term", "expected_industry"),
    [
        ("farmer", "Sheep farming: 01450"),
        ("consultant creating websites for clients", "Website design and development: 62012"),
    ],
)
def test_select_expected_activity_and_save(
    quick_test: QuickTestPage, search_term: str, expected_industry: str
) -> None:
    """Search for, select, and save the expected suggestion from SAYT results."""
    quick_test.search_and_select_expected_suggestion(search_term, expected_industry)
    quick_test.save()
    quick_test.expect_saved(expected_industry)


def test_suggestions_change_as_search_term_changes(quick_test: QuickTestPage) -> None:
    """Verify that live suggestions change as the user types and deletes text."""
    options = quick_test.get_suggestion_options()

    quick_test.type_text("farm", "farm")
    expect(options.nth(1)).to_be_visible()
    initial_suggestions = options.all_inner_texts()

    quick_test.type_text("ing sheep", "farming sheep")
    expect(options.nth(1)).to_be_visible()
    expect(options).not_to_have_text(initial_suggestions)
    refined_suggestions = options.all_inner_texts()

    quick_test.delete_activity_characters(6)
    expect(quick_test.activity).to_have_value("farming")
    expect(options.nth(1)).to_be_visible()
    expect(options).not_to_have_text(refined_suggestions)


def test_select_activity_not_listed_and_save(quick_test: QuickTestPage) -> None:
    """Save a self-described description when no suggestion is selected."""
    description = "Independent game design"
    quick_test.select_not_listed(description)
    quick_test.save()
    quick_test.expect_saved(description)
