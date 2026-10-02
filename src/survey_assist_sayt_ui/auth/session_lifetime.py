"""Calculate the absolute expiry of an authenticated session."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def login_deadline(raw_login_time: object, lifetime: timedelta) -> datetime:
    """Calculate a login's fixed UTC expiry.

    Args:
        raw_login_time: ISO-8601 login timestamp stored in the session.
        lifetime: Maximum authenticated session lifetime.

    Returns:
        The absolute UTC expiry time.

    Raises:
        ValueError: If the stored timestamp is absent, malformed, or naive.
    """
    if not isinstance(raw_login_time, str):
        raise ValueError("Authenticated session has no login timestamp")

    try:
        login_time = datetime.fromisoformat(raw_login_time)
    except ValueError as exc:
        raise ValueError("Authenticated session has an invalid login timestamp") from exc

    if login_time.tzinfo is None or login_time.utcoffset() is None:
        raise ValueError("Authenticated session login timestamp has no timezone")

    return login_time.astimezone(UTC) + lifetime
