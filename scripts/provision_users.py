#!/usr/bin/env python3
"""Add, update, or delete users in the lightweight authentication user store."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
from pathlib import Path
import sys

from google.cloud import storage

from survey_assist_sayt_ui.auth.user_management import (
    add_user,
    delete_user,
    load_users,
    normalise_username,
    save_users,
    update_user,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Add, update, or delete users in a users.json file."
    )
    parser.add_argument(
        "action",
        choices=("add", "update", "delete"),
        help="User management action to perform.",
    )
    parser.add_argument(
        "--username",
        required=True,
        help="User email address.",
    )
    parser.add_argument(
        "--password",
        help="Plaintext password. If omitted for add/update, you will be prompted.",
    )
    parser.add_argument(
        "--output",
        default="users.json",
        help="Local users file. Defaults to users.json.",
    )
    parser.add_argument(
        "--bucket",
        help="Optional GCS bucket to upload the updated users file to.",
    )
    parser.add_argument(
        "--blob",
        default="users.json",
        help="GCS blob name. Defaults to users.json.",
    )
    parser.add_argument(
        "--kms-key-name",
        help="Optional Cloud KMS key resource name for the uploaded object.",
    )
    return parser.parse_args()


def upload_users(
    users_file: Path,
    bucket_name: str,
    blob_name: str,
    kms_key_name: str | None,
) -> None:
    """Upload a users file to Google Cloud Storage.

    Args:
        users_file: Local users file.
        bucket_name: GCS bucket name.
        blob_name: GCS object name.
        kms_key_name: Optional customer-managed encryption key.
    """
    client = storage.Client()  # type: ignore[no-untyped-call]
    bucket = client.bucket(bucket_name)  # type: ignore[no-untyped-call]
    blob = bucket.blob(blob_name)

    if kms_key_name:
        blob.kms_key_name = kms_key_name

    blob.upload_from_filename(
        users_file,
        content_type="application/json",
    )

    logger.info("Uploaded gs://%s/%s", bucket_name, blob_name)


def _get_password(password: str | None) -> str:
    """Return a supplied or interactively entered password.

    Args:
        password: Optional command-line password.

    Returns:
        str: Plaintext password.

    Raises:
        ValueError: If the password is blank.
    """
    resolved_password = password if password is not None else getpass.getpass("Password: ")

    if not resolved_password:
        raise ValueError("Password must not be blank")

    return resolved_password


def main() -> int:
    """Run user management.

    Returns:
        int: Zero when user management succeeds.
    """
    args = parse_args()
    users_file = Path(args.output)
    users = load_users(users_file)

    username = normalise_username(args.username)

    if args.action == "add":
        users = add_user(users, username, _get_password(args.password))
        logger.info("Added user '%s'", username)
    elif args.action == "update":
        users = update_user(users, username, _get_password(args.password))
        logger.info("Updated user '%s'", username)
    else:
        users = delete_user(users, username)
        logger.info("Deleted user '%s'", username)

    save_users(users_file, users)
    logger.info("Wrote %s", users_file)

    if args.bucket:
        upload_users(
            users_file=users_file,
            bucket_name=args.bucket,
            blob_name=args.blob,
            kms_key_name=args.kms_key_name,
        )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(2)
