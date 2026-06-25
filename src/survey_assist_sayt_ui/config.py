"""Application configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:  # pylint: disable=too-many-instance-attributes
    """Runtime settings loaded from environment variables.

    Attributes:
        secret_key: Secret key used for Flask session signing.
        sayt_api_url: URL of the search as yout type API endpoint.
        service_name: Service display name.
        auth_mode: Authentication backend mode.
        local_users_file: Local JSON file path for users.
        gcp_auth_bucket_name: Optional GCS bucket name for users JSON.
        gcp_auth_blob_name: Blob name within the configured bucket.
        session_cookie_secure: Whether session cookies are HTTPS-only.
    """

    secret_key: str
    sayt_api_url: str
    service_name: str = "Survey Assist SAYT UI"
    auth_mode: str = "local"
    local_users_file: str = "users.json"
    gcp_auth_bucket_name: str | None = None
    gcp_auth_blob_name: str = "users.json"
    session_cookie_secure: bool = False


def _bool_from_env(name: str, default: bool = False) -> bool:
    """Convert an environment variable to a boolean value.

    Args:
        name: Environment variable name.
        default: Default value when the variable is unset.

    Returns:
        bool: Parsed boolean value.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_settings() -> Settings:
    """Load runtime settings from environment variables.

    Returns:
        Settings: Resolved immutable settings object.
    """
    return Settings(
        secret_key=os.getenv("FLASK_SECRET_KEY", "dev-only-change-me"),
        sayt_api_url=_required_env("SAYT_API_URL"),
        service_name=os.getenv("SERVICE_NAME", "Survey Assist SAYT UI"),
        auth_mode=os.getenv("AUTH_MODE", "local").strip().lower(),
        local_users_file=os.getenv("LOCAL_USERS_FILE", "users.json"),
        gcp_auth_bucket_name=os.getenv("GCP_AUTH_BUCKET_NAME"),
        gcp_auth_blob_name=os.getenv("GCP_AUTH_BLOB_NAME", "users.json"),
        session_cookie_secure=_bool_from_env("SESSION_COOKIE_SECURE", False),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"{name} must be configured")

    return value
