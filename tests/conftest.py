"""Shared pytest fixtures for the Survey Assist SAYT UI."""

from collections.abc import Callable, Iterator

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.service import AuthService, AuthStore
from survey_assist_sayt_ui.config import Settings

TokenRefresher = Callable[[int, str, str, str], tuple[int, str]]


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


def _static_token_refresher(
    token_start_time: int,
    current_token: str,
    api_gateway: str,
    sa_email: str,
) -> tuple[int, str]:
    """Return a deterministic token without contacting Google IAM."""
    assert api_gateway == "0.0.0.0:8080"
    assert sa_email == "sayt-ui@example.iam.gserviceaccount.com"

    return (
        token_start_time or 1_700_000_000,
        current_token or "test-jwt-token",
    )


@pytest.fixture
def static_token_refresher() -> TokenRefresher:
    """Provide a deterministic token refresher for tests."""
    return _static_token_refresher


@pytest.fixture(name="app")
def app_fixture(
    static_token_refresher: TokenRefresher,
) -> Flask:
    """Create a configured Flask application for tests.

    Returns:
        Flask: Test application instance.
    """
    settings = Settings(
        secret_key="test-secret-key",  # pragma: allowlist secret
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        sa_email="sayt-ui@example.iam.gserviceaccount.com",
        service_name="Survey Assist SAYT UI",
        auth_mode="local",
        session_cookie_secure=False,
    )

    application = create_app(
        settings=settings,
        auth_service=AuthService(StaticAuthStore()),
        token_refresher=static_token_refresher,
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
