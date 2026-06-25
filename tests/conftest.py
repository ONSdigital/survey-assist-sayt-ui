"""Shared pytest fixtures for the Survey Assist SAYT UI."""

from collections.abc import Iterator

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.service import AuthService, AuthStore
from survey_assist_sayt_ui.config import Settings


class StaticAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Provide a fixed set of authentication users for tests."""

    def __init__(self, users: dict[str, str] | None = None) -> None:
        """Initialise the test authentication store.

        Args:
            users: Optional mapping of usernames to password hashes.
        """
        self.users = users or {}

    def load_users(self) -> dict[str, str]:
        """Return the configured users.

        Returns:
            dict[str, str]: Configured username and password hash mapping.
        """
        return self.users


@pytest.fixture(name="app")
def app_fixture() -> Flask:
    """Create a configured Flask application for tests.

    Returns:
        Flask: Test application instance.
    """
    settings = Settings(
        secret_key="test-secret-key",  # pragma: allowlist secret
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        service_name="Survey Assist SAYT UI",
        auth_mode="local",
        session_cookie_secure=False,
    )

    application = create_app(
        settings=settings,
        auth_service=AuthService(StaticAuthStore()),
    )
    application.config.update(TESTING=True)

    return application


@pytest.fixture(name="client")
def client_fixture(app: Flask) -> Iterator[FlaskClient]:
    """Create a Flask test client.

    Args:
        app: Configured Flask application.

    Yields:
        FlaskClient: Client for making test HTTP requests.
    """
    with app.test_client() as test_client:
        yield test_client
