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
from survey_assist_sayt_ui.survey.models import SurveyDefinition


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
    assert "Shape Tomorrow Prototype" in response_text
    assert "Begin study" in response_text
    assert 'href="#data-protection"' in response_text


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
