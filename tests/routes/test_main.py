"""Tests for the main UI routes."""

from http import HTTPStatus

from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.auth.decorators import (
    POST_LOGIN_REDIRECT_KEY,
    SESSION_USER_KEY,
)


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
