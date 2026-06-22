"""Authentication service and user-store loading."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Any

from google.cloud import storage

from ons_flask_auth_template.config import Settings

from .password_utils import verify_password

logger = logging.getLogger(__name__)


class AuthStore(ABC):  # pylint: disable=too-few-public-methods
    """Interface for loading registered users."""

    @abstractmethod
    def load_users(self) -> dict[str, str]:
        """Load registered users from the backing store.

        Returns:
            dict[str, str]: Mapping of normalised username to password hash.
        """


class LocalJsonAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Load registered users from a local JSON file."""

    def __init__(self, users_file: str | Path) -> None:
        """Initialise the local JSON auth store.

        Args:
            users_file: Path to the local users JSON file.
        """
        self.users_file = Path(users_file)

    def load_users(self) -> dict[str, str]:
        """Load users from the configured local file.

        Returns:
            dict[str, str]: Mapping of normalised username to password hash.

        Raises:
            FileNotFoundError: If the configured users file does not exist.
        """
        if not self.users_file.exists():
            raise FileNotFoundError(f"Local users file not found: {self.users_file}")
        return _parse_users_payload(self.users_file.read_text(encoding="utf-8"))


class GcsJsonAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Load registered users from a JSON object in Google Cloud Storage."""

    def __init__(
        self,
        bucket_name: str,
        blob_name: str = "users.json",
        client: storage.Client | None = None,
    ) -> None:
        """Initialise the GCS auth store.

        Args:
            bucket_name: Name of the GCS bucket containing users JSON.
            blob_name: Blob path for the users JSON object.
            client: Optional pre-configured storage client.
        """
        self.bucket_name = bucket_name
        self.blob_name = blob_name
        self.client = client

    def _client(self) -> storage.Client:
        """Return a cached storage client.

        Returns:
            storage.Client: Client used to access Cloud Storage.
        """
        if self.client is None:
            self.client = storage.Client()  # type: ignore[no-untyped-call]
        return self.client

    def load_users(self) -> dict[str, str]:
        """Load users from the configured GCS object.

        Returns:
            dict[str, str]: Mapping of normalised username to password hash.
        """
        bucket = self._client().bucket(self.bucket_name)  # type: ignore[no-untyped-call]
        blob = bucket.blob(self.blob_name)
        logger.info("Loading auth users from gs://%s/%s", self.bucket_name, self.blob_name)
        return _parse_users_payload(blob.download_as_text(encoding="utf-8"))


class AuthService:  # pylint: disable=too-few-public-methods
    """Validate user credentials against a configured auth store."""

    def __init__(self, auth_store: AuthStore) -> None:
        """Initialise the authentication service.

        Args:
            auth_store: Store implementation used to load registered users.
        """
        self.auth_store = auth_store

    def credentials_match(self, username: str, password: str) -> bool:
        """Check whether supplied credentials are valid.

        Args:
            username: Submitted username or email address.
            password: Submitted plain text password.

        Returns:
            bool: True when credentials match a registered user.
        """
        normalised_username = username.strip().lower()
        try:
            registered_users = self.auth_store.load_users()
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            logger.exception("Failed to load registered users: %s", exc)
            return False

        stored_hash = registered_users.get(normalised_username)
        if not stored_hash:
            return False
        return verify_password(stored_hash, password)


def build_auth_store(settings: Settings) -> AuthStore:
    """Build an auth store from application settings.

    Args:
        settings: Application settings used to resolve auth backend.

    Returns:
        AuthStore: Local or GCS auth store implementation.

    Raises:
        ValueError: If required GCS configuration is missing.
    """
    if settings.auth_mode == "gcs":
        if not settings.gcp_auth_bucket_name:
            raise ValueError("GCP_AUTH_BUCKET_NAME must be set when AUTH_MODE=gcs")
        return GcsJsonAuthStore(
            bucket_name=settings.gcp_auth_bucket_name,
            blob_name=settings.gcp_auth_blob_name,
        )
    return LocalJsonAuthStore(settings.local_users_file)


def _parse_users_payload(raw_payload: str) -> dict[str, str]:
    """Parse supported users JSON payload formats.

    Args:
        raw_payload: Raw JSON text from a local file or GCS object.

    Returns:
        dict[str, str]: Mapping of normalised username to password hash.

    Raises:
        ValueError: If the payload format is unsupported.
    """
    parsed_payload: Any = json.loads(raw_payload)

    if isinstance(parsed_payload, dict) and "users" not in parsed_payload:
        return {
            str(username).strip().lower(): str(password_hash)
            for username, password_hash in parsed_payload.items()
        }

    records = parsed_payload.get("users") if isinstance(parsed_payload, dict) else parsed_payload
    if not isinstance(records, list):
        raise ValueError("users.json must contain a dictionary or a list of user records")

    users: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        username = str(record.get("username") or record.get("email") or "").strip().lower()
        password_hash = str(record.get("password_hash") or record.get("password") or "")
        if username and password_hash:
            users[username] = password_hash
    return users
