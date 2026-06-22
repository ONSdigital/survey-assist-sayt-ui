#!/usr/bin/env python3
"""Create or upload a hashed users.json file for lightweight authentication."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
from pathlib import Path
import sys

from google.cloud import storage
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    """Provision hashed users and optionally upload to Cloud Storage.

    Returns:
        int: Zero when provisioning succeeds.
    """
    parser = argparse.ArgumentParser(description="Provision users for the Flask auth template.")
    parser.add_argument(
        "--user",
        action="append",
        default=[],
        metavar="EMAIL:PASSWORD",
        help="User to add. Can be supplied more than once. Omit to be prompted.",
    )
    parser.add_argument("--output", default="users.json", help="Local output path.")
    parser.add_argument("--bucket", help="Optional GCS bucket to upload the users file to.")
    parser.add_argument(
        "--blob", default="users.json", help="GCS blob name. Defaults to users.json."
    )
    parser.add_argument(
        "--kms-key-name",
        help="Optional Cloud KMS key resource name used as object customer-managed encryption key",
    )
    args = parser.parse_args()

    raw_users = args.user or [_prompt_for_user()]
    users = [_parse_user(raw_user) for raw_user in raw_users]
    payload = {"users": users}

    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", output_path)

    if args.bucket:
        client = storage.Client()
        bucket = client.bucket(args.bucket)
        blob = bucket.blob(args.blob)
        if args.kms_key_name:
            blob.kms_key_name = args.kms_key_name
        blob.upload_from_filename(output_path, content_type="application/json")
        logger.info("Uploaded gs://%s/%s", args.bucket, args.blob)

    return 0


def _prompt_for_user() -> str:
    """Prompt for one user in ``email:password`` format.

    Returns:
        str: A single ``email:password`` value from interactive input.
    """
    email = input("Email address: ").strip().lower()
    password = getpass.getpass("Password: ")
    return f"{email}:{password}"


def _parse_user(raw_user: str) -> dict[str, str]:
    """Parse and hash an individual user credential pair.

    Args:
        raw_user: User credentials in ``EMAIL:PASSWORD`` format.

    Returns:
        dict[str, str]: A user record with normalised username and password hash.

    Raises:
        ValueError: If the input is not in the expected format or values are blank.
    """
    if ":" not in raw_user:
        raise ValueError("--user must be in EMAIL:PASSWORD format")
    username, password = raw_user.split(":", 1)
    username = username.strip().lower()
    if not username or not password:
        raise ValueError("Both email and password are required")
    return {"username": username, "password_hash": generate_password_hash(password)}


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(2)
