"""Tests for the authentication service and stores."""

import json
from pathlib import Path
from typing import cast

from google.cloud import storage
import pytest

from survey_assist_sayt_ui.auth import service as service_module
from survey_assist_sayt_ui.auth.service import (
    AuthService,
    AuthStore,
    GcsJsonAuthStore,
    LocalJsonAuthStore,
    build_auth_store,
)
from survey_assist_sayt_ui.config import Settings


class StaticAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Provide fixed authentication data for service tests."""

    def __init__(self, users: dict[str, str]) -> None:
        """Initialise the authentication store.

        Args:
            users: Mapping of usernames to password hashes.
        """
        self.users = users

    def load_users(self) -> dict[str, str]:
        """Return the configured users.

        Returns:
            dict[str, str]: Configured authentication users.
        """
        return self.users


class FailingAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Raise a configured exception when users are loaded."""

    def __init__(self, error: Exception) -> None:
        """Initialise the failing authentication store.

        Args:
            error: Exception to raise when loading users.
        """
        self.error = error

    def load_users(self) -> dict[str, str]:
        """Raise the configured exception.

        Raises:
            Exception: Always raises the configured exception.
        """
        raise self.error


class FakeBlob:  # pylint: disable=too-few-public-methods
    """Represent a fake Google Cloud Storage blob."""

    def __init__(self, payload: str) -> None:
        """Initialise the fake blob.

        Args:
            payload: Text returned when the blob is downloaded.
        """
        self.payload = payload

    def download_as_text(self, encoding: str = "utf-8") -> str:
        """Return the configured blob payload.

        Args:
            encoding: Requested text encoding.

        Returns:
            str: Configured blob payload.
        """
        assert encoding == "utf-8"
        return self.payload


class FakeBucket:  # pylint: disable=too-few-public-methods
    """Represent a fake Google Cloud Storage bucket."""

    def __init__(self, payload: str) -> None:
        """Initialise the fake bucket.

        Args:
            payload: Payload returned by blobs in the bucket.
        """
        self.payload = payload
        self.requested_blob_name: str | None = None

    def blob(self, blob_name: str) -> FakeBlob:
        """Return a fake blob.

        Args:
            blob_name: Requested blob name.

        Returns:
            FakeBlob: Blob containing the configured payload.
        """
        self.requested_blob_name = blob_name
        return FakeBlob(self.payload)


class FakeStorageClient:  # pylint: disable=too-few-public-methods
    """Represent a fake Google Cloud Storage client."""

    def __init__(self, payload: str) -> None:
        """Initialise the fake storage client.

        Args:
            payload: Payload returned by the fake bucket.
        """
        self.bucket_instance = FakeBucket(payload)
        self.requested_bucket_name: str | None = None

    def bucket(self, bucket_name: str) -> FakeBucket:
        """Return the fake bucket.

        Args:
            bucket_name: Requested bucket name.

        Returns:
            FakeBucket: Configured fake bucket.
        """
        self.requested_bucket_name = bucket_name
        return self.bucket_instance


def test_local_store_raises_when_users_file_is_missing(
    tmp_path: Path,
) -> None:
    """Test that a missing local users file raises an error."""
    users_file = tmp_path / "missing-users.json"
    store = LocalJsonAuthStore(users_file)

    with pytest.raises(
        FileNotFoundError,
        match="Local users file not found",
    ):
        store.load_users()


def test_local_store_loads_dictionary_payload(tmp_path: Path) -> None:
    """Test loading users from a dictionary payload."""
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            {
                " Person@Example.com ": "hash-one",
                "SECOND@EXAMPLE.COM": "hash-two",
            }
        ),
        encoding="utf-8",
    )

    store = LocalJsonAuthStore(users_file)

    assert store.load_users() == {
        "person@example.com": "hash-one",
        "second@example.com": "hash-two",
    }


def test_local_store_loads_wrapped_user_records(tmp_path: Path) -> None:
    """Test loading users from a wrapped list of user records."""
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": " Person@Example.com ",
                        "password_hash": "hash-one",  # pragma: allowlist secret
                    },
                    {
                        "email": "SECOND@EXAMPLE.COM",
                        "password": "hash-two",  # pragma: allowlist secret
                    },
                    "invalid-record",
                    {"username": "", "password_hash": "missing-name"},  # pragma: allowlist secret
                    {"username": "missing-password@example.com"},
                ]
            }
        ),
        encoding="utf-8",
    )

    store = LocalJsonAuthStore(users_file)

    assert store.load_users() == {
        "person@example.com": "hash-one",
        "second@example.com": "hash-two",
    }


def test_local_store_loads_top_level_list(tmp_path: Path) -> None:
    """Test loading users from a top-level list."""
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            [
                {
                    "username": "person@example.com",
                    "password_hash": "password-hash",  # pragma: allowlist secret
                }
            ]
        ),
        encoding="utf-8",
    )

    store = LocalJsonAuthStore(users_file)

    assert store.load_users() == {
        "person@example.com": "password-hash",
    }


def test_local_store_rejects_unsupported_payload(tmp_path: Path) -> None:
    """Test that an unsupported payload raises a validation error."""
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps({"users": "not-a-list"}),
        encoding="utf-8",
    )

    store = LocalJsonAuthStore(users_file)

    with pytest.raises(
        ValueError,
        match="must contain a dictionary or a list",
    ):
        store.load_users()


def test_gcs_store_loads_and_normalises_users() -> None:
    """Test loading users from Google Cloud Storage."""
    fake_client = FakeStorageClient(json.dumps({"Person@Example.com": "password-hash"}))
    store = GcsJsonAuthStore(
        bucket_name="auth-bucket",
        blob_name="authentication/users.json",
        client=cast(storage.Client, fake_client),
    )

    users = store.load_users()

    assert users == {"person@example.com": "password-hash"}
    assert fake_client.requested_bucket_name == "auth-bucket"
    assert fake_client.bucket_instance.requested_blob_name == "authentication/users.json"


def test_credentials_match_normalises_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test matching credentials with a normalised username."""
    service = AuthService(StaticAuthStore({"person@example.com": "stored-password-hash"}))

    def password_matches(stored_hash: str, password: str) -> bool:
        """Check the values passed to password verification."""
        return (
            stored_hash == "stored-password-hash"
            and password == "submitted-password"  # pragma: allowlist secret
        )

    monkeypatch.setattr(
        service_module,
        "verify_password",
        password_matches,
    )

    assert service.credentials_match(
        " Person@Example.com ",
        "submitted-password",
    )


def test_credentials_do_not_match_unknown_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that an unknown username does not invoke hash verification."""
    service = AuthService(StaticAuthStore({"person@example.com": "stored-password-hash"}))

    def unexpected_password_check(
        _stored_hash: str,
        _password: str,
    ) -> bool:
        """Fail if password verification is unexpectedly invoked."""
        pytest.fail("Password verification should not be called")

    monkeypatch.setattr(
        service_module,
        "verify_password",
        unexpected_password_check,
    )

    assert not service.credentials_match(
        "unknown@example.com",
        "submitted-password",
    )


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("missing file"),
        ValueError("invalid users payload"),
        json.JSONDecodeError("invalid JSON", "invalid", 0),
    ],
)
def test_credentials_do_not_match_when_store_loading_fails(
    error: Exception,
) -> None:
    """Test that supported store failures are handled safely.

    Args:
        error: Store-loading exception raised during the test.
    """
    service = AuthService(FailingAuthStore(error))

    assert not service.credentials_match(
        "person@example.com",
        "submitted-password",
    )


def test_build_auth_store_returns_local_store() -> None:
    """Test building a local authentication store."""
    settings = Settings(
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        sa_email="sayt-ui@example.iam.gserviceaccount.com",
        secret_key="test-secret",  # pragma: allowlist secret
        auth_mode="local",
        local_users_file="test-users.json",
    )

    store = build_auth_store(settings)

    assert isinstance(store, LocalJsonAuthStore)
    assert store.users_file == Path("test-users.json")


def test_build_auth_store_returns_gcs_store() -> None:
    """Test building a Google Cloud Storage authentication store."""
    settings = Settings(
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        sa_email="sayt-ui@example.iam.gserviceaccount.com",
        secret_key="test-secret",  # pragma: allowlist secret
        auth_mode="gcs",
        gcp_auth_bucket_name="auth-bucket",
        gcp_auth_blob_name="config/users.json",
    )

    store = build_auth_store(settings)

    assert isinstance(store, GcsJsonAuthStore)
    assert store.bucket_name == "auth-bucket"
    assert store.blob_name == "config/users.json"


def test_build_auth_store_requires_gcs_bucket() -> None:
    """Test that GCS mode requires a configured bucket."""
    settings = Settings(
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        sa_email="sayt-ui@example.iam.gserviceaccount.com",
        secret_key="test-secret",  # pragma: allowlist secret
        auth_mode="gcs",
        gcp_auth_bucket_name=None,
    )

    with pytest.raises(
        ValueError,
        match="GCP_AUTH_BUCKET_NAME must be set",
    ):
        build_auth_store(settings)
