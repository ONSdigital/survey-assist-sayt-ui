"""User management helpers for the lightweight authentication store."""

from __future__ import annotations

import json
from pathlib import Path

from survey_assist_sayt_ui.auth.password_utils import hash_password

UserRecord = dict[str, str]


def load_users(users_file: Path) -> list[UserRecord]:
    """Load users from a local JSON file."""
    if not users_file.exists():
        return []

    payload = json.loads(users_file.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("users.json must contain a JSON object")

    records = payload.get("users")
    if not isinstance(records, list):
        raise ValueError("users.json must contain a 'users' list")

    users: list[UserRecord] = []

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each user record must be a JSON object")

        username = str(record.get("username", "")).strip().lower()
        password_hash = str(record.get("password_hash", ""))

        if not username or not password_hash:
            raise ValueError("Each user record must contain 'username' and 'password_hash'")

        users.append(
            {
                "username": username,
                "password_hash": password_hash,
            }
        )

    return users


def add_user(
    users: list[UserRecord],
    username: str,
    password: str,
) -> list[UserRecord]:
    """Add a new user."""
    normalised_username = normalise_username(username)

    if _find_user(users, normalised_username) is not None:
        raise ValueError(
            f"User '{normalised_username}' already exists. " "Use 'update' to change the password."
        )

    users.append(
        {
            "username": normalised_username,
            "password_hash": hash_password(password),
        }
    )
    users.sort(key=lambda user: user["username"])

    return users


def update_user(
    users: list[UserRecord],
    username: str,
    password: str,
) -> list[UserRecord]:
    """Update an existing user's password."""
    normalised_username = normalise_username(username)
    user_index = _find_user(users, normalised_username)

    if user_index is None:
        raise ValueError(f"User '{normalised_username}' does not exist")

    users[user_index] = {
        "username": normalised_username,
        "password_hash": hash_password(password),
    }

    return users


def delete_user(
    users: list[UserRecord],
    username: str,
) -> list[UserRecord]:
    """Delete an existing user."""
    normalised_username = normalise_username(username)
    user_index = _find_user(users, normalised_username)

    if user_index is None:
        raise ValueError(f"User '{normalised_username}' does not exist")

    del users[user_index]
    return users


def save_users(users_file: Path, users: list[UserRecord]) -> None:
    """Save users to disk."""
    payload = {"users": users}

    users_file.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _find_user(users: list[UserRecord], username: str) -> int | None:
    """Find a user index by username."""
    for index, user in enumerate(users):
        if user["username"] == username:
            return index

    return None


def normalise_username(username: str) -> str:
    """Normalise a username."""
    normalised_username = username.strip().lower()

    if not normalised_username:
        raise ValueError("Username must not be blank")

    return normalised_username
