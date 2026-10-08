"""Browser test for the sandbox sign-in, survey, and sign-out journey."""

import re

from playwright.sync_api import Page, expect


def test_sign_in_select_business_activity_and_sign_out(
    page: Page,
    base_url: str,
    credentials: tuple[str, str],
) -> None:
    """Select a game developer suggestion and sign out."""
    username, password = credentials

    page.goto(f"{base_url}/")
    expect(page).to_have_url(re.compile(r"/login$"))

    page.get_by_label("Email address").fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Login").click()
    expect(
        page.get_by_text(f"You are signed in as {username.strip().lower()}.", exact=True)
    ).to_be_visible()

    page.get_by_role("button", name="SAYT Quick Test").click()
    expect(page).to_have_url(re.compile(r"/api-autosuggest"))

    activity = page.get_by_role("combobox")
    activity.fill("game developer")
    suggestion = (
        page.get_by_role("listbox", name="Suggested industries").get_by_role("option").first
    )
    expect(suggestion).to_be_visible()
    selected_activity = suggestion.inner_text()

    suggestion.click()

    expect(activity).to_have_value(selected_activity)
    page.get_by_role("button", name="Save and continue").click()
    expect(
        page.get_by_text(f'Your response "{selected_activity}" has been saved successfully.')
    ).to_be_visible()

    page.get_by_role("button", name="Sign out").click()
    expect(page).to_have_url(re.compile(r"/login$"))
