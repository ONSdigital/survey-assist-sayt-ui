"""Configure the Flask session storage backend."""

import logging

from flask import Flask
from flask_session import Session
from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from survey_assist_sayt_ui.config import Settings

logger = logging.getLogger(__name__)


def _positive_int(name: str, raw: str, *, maximum: int | None = None) -> int:
    """Parse and validate a positive integer configuration value.

    Args:
        name: Configuration setting name, used in validation errors.
        raw: String value to parse as an integer.
        maximum: Optional inclusive upper bound for the parsed value.

    Returns:
        The parsed positive integer.

    Raises:
        ValueError: If ``raw`` is not an integer or is outside the allowed range.
    """
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value < 1 or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be between 1 and {maximum or 'unbounded'}")

    return value


def configure_session(app: Flask, settings: Settings) -> None:
    """Configure the Flask session backend from application settings.

    Client-side sessions are left unchanged. For Redis sessions, this validates
    the connection settings, verifies Redis availability, and initializes
    Flask-Session with the configured Redis client.

    Args:
        app: Flask application whose session configuration will be updated.
        settings: Application settings containing session backend details.

    Raises:
        ValueError: If the backend or its required Redis settings are invalid.
        RuntimeError: If Redis is unavailable or does not acknowledge the ping.
    """
    backend = settings.session_backend.strip().lower()

    if backend == "client":
        return
    if backend != "redis":
        raise ValueError("SESSION_BACKEND must be 'client' or 'redis'")

    host = settings.redis_host
    if host is None or not host.strip():
        raise ValueError("REDIS_HOST is required when SESSION_BACKEND=redis")

    port = _positive_int("REDIS_PORT", settings.redis_port, maximum=65535)
    max_connections = _positive_int("REDIS_MAX_CONNECTIONS", settings.redis_max_connections)

    pool = ConnectionPool(
        host=host.strip(),
        port=port,
        max_connections=max_connections,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    redis_client = Redis(connection_pool=pool)

    try:
        available = redis_client.ping()
    except RedisError as exc:
        logger.critical("Redis session store unavailable at startup", exc_info=True)
        raise RuntimeError("Redis session store unavailable at startup") from exc

    if not available:
        logger.critical("Redis session store did not acknowledge startup ping")
        raise RuntimeError("Redis session store did not acknowledge startup ping")

    app.config.update(
        SESSION_TYPE="redis",
        SESSION_REDIS=redis_client,
        SESSION_SERIALIZATION_FORMAT="msgpack",
        SESSION_KEY_PREFIX="sayt-ui:session:",
        SESSION_PERMANENT=False,
        SESSION_REFRESH_EACH_REQUEST=False,
    )
    Session(app)  # type: ignore[no-untyped-call]
