"""Authentication flow tests for the Flask app."""

from __future__ import annotations

import json
from pathlib import Path

from werkzeug.security import generate_password_hash

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.config import Settings


def test_protected_index_redirects_to_login(tmp_path: Path) -> None:
    """Ensure protected routes redirect unauthenticated users.

    Args:
        tmp_path: Temporary directory fixture for test files.
    """
    users_file = tmp_path / "users.json"
    users_file.write_text('{"users": []}', encoding="utf-8")
    app = create_app(Settings(secret_key="test", local_users_file=str(users_file)))
    app.testing = True

    response = app.test_client().get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_can_log_in_with_valid_credentials(tmp_path: Path) -> None:
    """Ensure valid credentials create an authenticated session.

    Args:
        tmp_path: Temporary directory fixture for test files.
    """
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "person@example.com",
                        "password_hash": generate_password_hash("secret-password"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    app = create_app(Settings(secret_key="test", local_users_file=str(users_file)))
    app.testing = True

    response = app.test_client().post(
        "/check-login",
        data={
            "username": "person@example.com",
            "password": "secret-password",  # pragma: allowlist secret
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
