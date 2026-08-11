"""Tests for the user provisioning script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from survey_assist_sayt_ui.auth.password_utils import verify_password
from survey_assist_sayt_ui.auth.user_management import (
    add_user,
    delete_user,
    load_users,
    save_users,
    update_user,
)

EXISTING_HASH = "existing-hash"  # pragma: allowlist secret
FIRST_HASH = "first-hash"  # pragma: allowlist secret
SECOND_HASH = "second-hash"  # pragma: allowlist secret
STORED_HASH = "stored-hash"  # pragma: allowlist secret


def test_load_users_returns_empty_list_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    """Missing users files should represent an empty user store."""
    users = load_users(tmp_path / "users.json")

    assert not users


def test_add_user_preserves_existing_users() -> None:
    """Adding a user must not replace existing users."""
    users = [
        {
            "username": "existing@example.com",
            "password_hash": EXISTING_HASH,
        }
    ]

    updated_users = add_user(
        users,
        "NEW@example.com",
        "new-password",
    )

    assert len(updated_users) == 2
    assert updated_users[0] == {
        "username": "existing@example.com",
        "password_hash": EXISTING_HASH,
    }

    new_user = updated_users[1]
    assert new_user["username"] == "new@example.com"
    assert verify_password(new_user["password_hash"], "new-password")


def test_add_existing_user_fails() -> None:
    """Adding an existing user should require an explicit update."""
    users = [
        {
            "username": "existing@example.com",
            "password_hash": EXISTING_HASH,
        }
    ]

    with pytest.raises(ValueError, match="already exists"):
        add_user(users, "existing@example.com", "new-password")


def test_update_user_changes_only_selected_password() -> None:
    """Updating a user should retain all other user records."""
    users = [
        {
            "username": "first@example.com",
            "password_hash": FIRST_HASH,
        },
        {
            "username": "second@example.com",
            "password_hash": SECOND_HASH,
        },
    ]

    updated_users = update_user(
        users,
        "first@example.com",
        "replacement-password",
    )

    assert verify_password(
        updated_users[0]["password_hash"],
        "replacement-password",
    )
    assert updated_users[1] == {
        "username": "second@example.com",
        "password_hash": SECOND_HASH,
    }


def test_update_missing_user_fails() -> None:
    """Updating an unknown user should fail."""
    with pytest.raises(ValueError, match="does not exist"):
        update_user([], "missing@example.com", "password")


def test_delete_user_preserves_other_users() -> None:
    """Deleting one user should preserve all remaining users."""
    users = [
        {
            "username": "first@example.com",
            "password_hash": FIRST_HASH,
        },
        {
            "username": "second@example.com",
            "password_hash": SECOND_HASH,
        },
    ]

    updated_users = delete_user(users, "first@example.com")

    assert updated_users == [
        {
            "username": "second@example.com",
            "password_hash": SECOND_HASH,
        }
    ]


def test_delete_missing_user_fails() -> None:
    """Deleting an unknown user should fail."""
    with pytest.raises(ValueError, match="does not exist"):
        delete_user([], "missing@example.com")


def test_save_and_load_users(tmp_path: Path) -> None:
    """Saved user records should round-trip through users.json."""
    users_file = tmp_path / "users.json"
    users = [
        {
            "username": "user@example.com",
            "password_hash": STORED_HASH,
        }
    ]

    save_users(users_file, users)

    assert load_users(users_file) == users

    raw_payload = json.loads(users_file.read_text(encoding="utf-8"))
    assert raw_payload == {"users": users}
