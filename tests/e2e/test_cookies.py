"""Browser tests for cookie consent."""

import json

from playwright.sync_api import Page, expect
import pytest


def assert_cookie_choice(page: Page, additional_cookies: bool) -> None:
    """Check that the saved cookie policy matches the selected choice."""
    cookies = {cookie["name"]: cookie["value"] for cookie in page.context.cookies()}
    assert cookies["ons_cookie_message_displayed"] == "true"
    assert json.loads(cookies["ons_cookie_policy"].replace("'", '"')) == {
        "essential": True,
        "settings": additional_cookies,
        "usage": additional_cookies,
        "campaigns": additional_cookies,
    }


@pytest.mark.parametrize(
    ("button_name", "confirmation", "additional_cookies"),
    [
        ("Accept additional cookies", "You have accepted all additional cookies.", True),
        ("Reject additional cookies", "You have rejected all additional cookies.", False),
    ],
)
def test_cookie_choice_persists_after_reload(
    page: Page,
    button_name: str,
    confirmation: str,
    additional_cookies: bool,
) -> None:
    """Keep the selected consent after a page reload."""
    page.goto("/cookies")
    banner = page.get_by_role("region", name="Cookies banner")
    expect(banner).to_be_visible()
    banner.get_by_role("button", name=button_name).click()

    expect(banner.get_by_text(confirmation)).to_be_visible()
    expect(banner.get_by_role("button", name=button_name)).to_be_hidden()

    assert_cookie_choice(page, additional_cookies)

    banner.get_by_role("button", name="Hide").click()
    expect(banner).to_be_hidden()
    page.reload(wait_until="networkidle")
    expect(banner).to_be_hidden()
    assert_cookie_choice(page, additional_cookies)
