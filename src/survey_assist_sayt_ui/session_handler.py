"""Configure client-side or Redis-backed Flask sessions."""

from datetime import timedelta
import logging
from math import ceil

from flask import Flask
from flask_session.base import ServerSideSession
from flask_session.redis.redis import RedisSessionInterface
from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.auth.session_lifetime import login_deadline
from survey_assist_sayt_ui.config import Settings

logger = logging.getLogger(__name__)


def _positive_int(name: str, raw: str, *, maximum: int | None = None) -> int:
    """Parse a positive integer configuration value.

    Args:
        name: Environment variable name for an error message.
        raw: Unparsed value.
        maximum: Optional inclusive upper bound.

    Returns:
        Validated positive integer.

    Raises:
        ValueError: If the value is invalid or outside its allowed range.
    """
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value < 1 or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be between 1 and {maximum or 'unbounded'}")

    return value


class AbsoluteExpiryRedisSessionInterface(RedisSessionInterface):
    """Save authenticated Redis sessions with an expiry fixed at login."""

    def _upsert_session(
        self,
        session_lifetime: timedelta,
        session: ServerSideSession,
        store_id: str,
    ) -> None:
        """Write a session without extending an authenticated login.

        Args:
            session_lifetime: Configured maximum lifetime.
            session: Session being saved by Flask-Session.
            store_id: Redis key assigned to this session.

        Raises:
            ValueError: If an authenticated session has an invalid login time.
            RedisError: If Redis cannot save the session.
        """
        if not session.get(SESSION_USER_KEY):
            super()._upsert_session(session_lifetime, session, store_id)
            return

        deadline = login_deadline(
            session.get(SESSION_LOGIN_TIME_KEY),
            session_lifetime,
        )

        serializer = self.serializer
        if serializer is None:
            raise RuntimeError("Redis session serializer is not configured")

        self.client.set(
            name=store_id,
            value=serializer.encode(session),
            exat=ceil(deadline.timestamp()),
        )


def configure_session(app: Flask, settings: Settings) -> None:
    """Configure the session backend and the maximum login lifetime.

    Args:
        app: Flask application to configure.
        settings: Runtime application settings.

    Raises:
        ValueError: If session or Redis configuration is invalid.
        RuntimeError: If the configured Redis store is unavailable at startup.
    """
    lifetime_days = _positive_int(
        "SESSION_LIFETIME_DAYS",
        settings.session_lifetime_days,
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=lifetime_days)

    backend = settings.session_backend.strip().lower()

    if backend == "client":
        return
    if backend != "redis":
        raise ValueError("SESSION_BACKEND must be 'client' or 'redis'")

    host = settings.redis_host
    if host is None or not host.strip():
        raise ValueError("REDIS_HOST is required when SESSION_BACKEND=redis")

    port = _positive_int("REDIS_PORT", settings.redis_port, maximum=65535)
    max_connections = _positive_int(
        "REDIS_MAX_CONNECTIONS",
        settings.redis_max_connections,
    )

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

    app.session_interface = AbsoluteExpiryRedisSessionInterface(
        app=app,
        client=redis_client,
        key_prefix=app.config["SESSION_KEY_PREFIX"],
        permanent=app.config["SESSION_PERMANENT"],
        serialization_format=app.config["SESSION_SERIALIZATION_FORMAT"],
    )
