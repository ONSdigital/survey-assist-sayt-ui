"""Tests for the main UI routes."""

from http import HTTPStatus
from typing import cast

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.auth.decorators import (
    POST_LOGIN_REDIRECT_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.services.business_activity import BusinessActivitySuggestion
from survey_assist_sayt_ui.survey.models import SurveyDefinition


class StubBusinessActivitySearchClient:  # pylint: disable=too-few-public-methods
    """Provide deterministic business activity suggestions for route tests."""

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Return fixed business activity suggestions."""
        assert query == "soft"
        assert limit == 20

        return [
            BusinessActivitySuggestion(
                label="Software development: 62012",
            ),
            BusinessActivitySuggestion(
                label="Soft drinks production: 11070",
            ),
        ]


def test_index_redirects_unauthenticated_user(
    client: FlaskClient,
) -> None:
    """Test that the landing page requires authentication."""
    response = client.get("/")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as flask_session:
        assert flask_session[POST_LOGIN_REDIRECT_KEY] == "/"


def test_index_renders_for_authenticated_user(
    client: FlaskClient,
) -> None:
    """Test rendering the landing page for an authenticated user."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/")

    assert response.status_code == HTTPStatus.OK
    assert "person@example.com" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("route", "expected_text"),
    [
        ("/cookies", "Cookies"),
        ("/accessibility", "Accessibility"),
        ("/privacy", "Privacy"),
    ],
)
def test_information_page_renders(
    client: FlaskClient,
    route: str,
    expected_text: str,
) -> None:
    """Test rendering a public information page.

    Args:
        client: Flask test client.
        route: Route being tested.
        expected_text: Text expected in the rendered response.
    """
    response = client.get(route)

    assert response.status_code == HTTPStatus.OK
    assert expected_text in response.get_data(as_text=True)


def test_health_returns_service_status(client: FlaskClient) -> None:
    """Test that the health endpoint returns a successful status."""
    response = client.get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {"status": "ok"}


def test_wireframe_renders_configured_intro(
    client: FlaskClient,
) -> None:
    """Test that the configured introduction is rendered."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/wireframe")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Test survey" in response_text
    assert "Begin study" in response_text


def test_wireframe_returns_not_found_when_intro_is_disabled(
    app: Flask,
    client: FlaskClient,
) -> None:
    """Test that a disabled introduction cannot be accessed directly."""
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_intro"]["enabled"] = False

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/wireframe")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_index_hides_wireframe_button_when_intro_is_disabled(
    app: Flask,
    client: FlaskClient,
) -> None:
    """Test that the landing page hides the disabled introduction."""
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_intro"]["enabled"] = False

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/")

    assert response.status_code == HTTPStatus.OK
    assert "Wireframe" not in response.get_data(as_text=True)


def test_business_activity_suggestions_rejects_query_over_maximum_length(
    client: FlaskClient,
) -> None:
    """Test that autosuggest queries longer than 100 characters are rejected."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get(
        "/api/business-activity-suggestions",
        query_string={"q": "a" * 101},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.get_json() == {
        "error": "Search query is too long",
    }


def test_business_activity_suggestions_returns_search_results(
    app: Flask,
    client: FlaskClient,
) -> None:
    """Test returning business activity suggestions to the autosuggest component."""
    app.extensions["business_activity_search_client"] = StubBusinessActivitySearchClient()

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get(
        "/api/business-activity-suggestions",
        query_string={"q": "soft"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == [
        {
            "en": "Software development: 62012",
        },
        {
            "en": "Soft drinks production: 11070",
        },
    ]


def test_api_autosuggest_renders_self_describe_input(
    client: FlaskClient,
) -> None:
    """Test API autosuggest renders the self-description control."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert 'id="business-activity-api-self-describe"' in response_text
    assert "Describe the main activity of your organisation" in response_text
    assert "autosuggest-self-describe.js" in response_text
    assert 'action="/api-autosuggest"' in response_text


def test_api_autosuggest_requires_self_description_for_not_listed(
    client: FlaskClient,
) -> None:
    """Test Not listed requires a free-text description."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.post(
        "/api-autosuggest",
        data={
            "business_activity": "",
            "business_activity_not_listed": "not-listed",
            "business_activity_self_describe": "   ",
        },
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Enter a description of the main activity of your organisation" in response_text
    assert 'id="business-activity-api-self-describe"' in response_text
    assert "checked" in response_text


def test_api_autosuggest_uses_self_description_for_not_listed(
    client: FlaskClient,
) -> None:
    """Test Not listed uses the supplied free-text description."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.post(
        "/api-autosuggest",
        data={
            "business_activity": "Software development: 62012",
            "business_activity_not_listed": "not-listed",
            "business_activity_self_describe": ("Repair and restoration of bicycles"),
        },
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Repair and restoration of bicycles" in response_text
    assert "Software development: 62012" not in response_text


def test_api_autosuggest_uses_selected_suggestion_when_not_listed_not_selected(
    client: FlaskClient,
) -> None:
    """Test the selected suggestion is used normally."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.post(
        "/api-autosuggest",
        data={
            "business_activity": "Software development: 62012",
            "business_activity_self_describe": "Ignored description",
        },
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Software development: 62012" in response_text
    assert "Ignored description" not in response_text


def test_api_autosuggest_rejects_invalid_not_listed_value(
    client: FlaskClient,
) -> None:
    """Test an invalid Not listed value is rejected."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.post(
        "/api-autosuggest",
        data={
            "business_activity_not_listed": "unexpected",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
