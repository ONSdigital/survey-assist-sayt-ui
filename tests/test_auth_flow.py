"""Integration tests for the Flask authentication flow."""

from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path

from werkzeug.security import generate_password_hash

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.decorators import SESSION_USER_KEY
from survey_assist_sayt_ui.config import Settings


def test_user_can_log_in_with_local_credentials(
    tmp_path: Path,
    static_token_refresher,
) -> None:
    """Test the complete local authentication flow.

    Args:
        tmp_path: Temporary directory used for the users file.
        static_token_refresher: Fixture providing a deterministic JWT for tests.
    """
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "person@example.com",
                        "password_hash": generate_password_hash(
                            "secret-password"  # pragma: allowlist secret
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    app = create_app(
        Settings(
            sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
            sa_email="sayt-ui@example.iam.gserviceaccount.com",
            secret_key="test-secret-key",  # pragma: allowlist secret
            local_users_file=str(users_file),
        ),
        token_refresher=static_token_refresher,
    )
    app.config.update(TESTING=True)

    client = app.test_client()
    response = client.post(
        "/check-login",
        data={
            "username": "person@example.com",
            "password": "secret-password",  # pragma: allowlist secret
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"] == "/"

    with client.session_transaction() as flask_session:
        assert flask_session[SESSION_USER_KEY] == "person@example.com"
