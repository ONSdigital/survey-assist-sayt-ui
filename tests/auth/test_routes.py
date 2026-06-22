"""Tests for authentication routes."""

from http import HTTPStatus

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.auth.decorators import (
    POST_LOGIN_REDIRECT_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.auth.service import AuthService


def test_login_renders_sign_in_page(client: FlaskClient) -> None:
    """Test that the login route renders the sign-in page."""
    response = client.get("/login")

    assert response.status_code == HTTPStatus.OK
    assert "Sign in" in response.get_data(as_text=True)


def test_login_redirects_authenticated_user(client: FlaskClient) -> None:
    """Test that an authenticated user is redirected from the login page."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"

    response = client.get("/login")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/")


def test_check_login_rejects_missing_credentials(client: FlaskClient) -> None:
    """Test that both username and password are required."""
    response = client.post(
        "/check-login",
        data={"username": "  ", "password": ""},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Enter your email address and password." in response.get_data(as_text=True)


def test_check_login_rejects_invalid_credentials(
    client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that invalid credentials return an unauthorised response."""
    auth_service = app.config["auth_service"]
    assert isinstance(auth_service, AuthService)

    def credentials_do_not_match(_username: str, _password: str) -> bool:
        """Return false for test credentials."""
        return False

    monkeypatch.setattr(
        auth_service,
        "credentials_match",
        credentials_do_not_match,
    )

    response = client.post(
        "/check-login",
        data={
            "username": " Person@Example.com ",
            "password": "incorrect-password",  # pragma: allowlist secret
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    response_text = response.get_data(as_text=True)
    assert "Invalid email address or password." in response_text
    assert "person@example.com" in response_text


def test_check_login_creates_session_and_redirects_to_index(
    client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that valid credentials create an authenticated session."""
    auth_service = app.config["auth_service"]
    assert isinstance(auth_service, AuthService)

    def credentials_match(_username: str, _password: str) -> bool:
        """Return true for test credentials."""
        return True

    monkeypatch.setattr(auth_service, "credentials_match", credentials_match)

    response = client.post(
        "/check-login",
        data={
            "username": " Person@Example.com ",
            "password": "correct-password",  # pragma: allowlist secret
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as flask_session:
        assert flask_session[SESSION_USER_KEY] == "person@example.com"


def test_check_login_redirects_to_original_protected_page(
    client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that login returns users to their original protected page."""
    auth_service = app.config["auth_service"]
    assert isinstance(auth_service, AuthService)

    def credentials_match(_username: str, _password: str) -> bool:
        """Return true for test credentials."""
        return True

    monkeypatch.setattr(auth_service, "credentials_match", credentials_match)

    with client.session_transaction() as flask_session:
        flask_session[POST_LOGIN_REDIRECT_KEY] = "/original-page"

    response = client.post(
        "/check-login",
        data={
            "username": "person@example.com",
            "password": "correct-password",  # pragma: allowlist secret
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/original-page")

    with client.session_transaction() as flask_session:
        assert POST_LOGIN_REDIRECT_KEY not in flask_session


def test_logout_clears_session_and_redirects_to_login(
    client: FlaskClient,
) -> None:
    """Test that logout clears authentication session data."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session["other-value"] = "value"

    response = client.get("/logout")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as flask_session:
        assert SESSION_USER_KEY not in flask_session
        assert "other-value" not in flask_session
