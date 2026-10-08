"""Configure client-side or Redis-backed Flask sessions."""

from collections.abc import Callable
from contextvars import ContextVar
from datetime import timedelta
import logging
from math import ceil
from typing import Any, TypeVar

from flask import Flask, Request, Response, render_template
from flask import request as flask_request
from flask.sessions import SessionMixin
from flask_session.base import ServerSideSession
from flask_session.redis.redis import RedisSessionInterface
from redis import ConnectionPool, Redis, RedisError
from redis.backoff import NoBackoff
from redis.connection import SSLConnection
from redis.exceptions import AuthenticationError, AuthorizationError, MaxConnectionsError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.auth.session_lifetime import login_deadline
from survey_assist_sayt_ui.config import Settings

logger = logging.getLogger(__name__)

READ_FAILURE_KEY = "survey_assist.redis_session_read_failed"
SAVE_OPERATION_KEY = "survey_assist.redis_session_save_operation"
RETRYABLE_REDIS_ERRORS = (RedisConnectionError, RedisTimeoutError)

RetryResult = TypeVar("RetryResult")


def _is_transient_redis_error(error: Exception) -> bool:
    """Identify Redis failures for which another attempt may succeed.

    Args:
        error: Failure raised by a Redis operation.

    Returns:
        Whether the failure is eligible for one retry.
    """
    return isinstance(error, RETRYABLE_REDIS_ERRORS) and not isinstance(
        error,
        (AuthenticationError, AuthorizationError, MaxConnectionsError),
    )


class SessionRetry(Retry):
    """Allow one transient retry across nested Redis command and connection calls."""

    _active: ContextVar[bool] = ContextVar(
        "survey_assist_redis_retry_active",
        default=False,
    )

    def call_with_retry(
        self,
        do: Callable[[], RetryResult],
        fail: Callable[[Exception], Any] | Callable[[Exception, int], Any],
        is_retryable: Callable[[Exception], bool] | None = None,
        with_failure_count: bool = False,
    ) -> RetryResult:
        """Run a Redis operation with the session retry policy.

        Args:
            do: Operation to execute.
            fail: Callback invoked after an eligible failure.
            is_retryable: Additional redis-py eligibility check, if supplied.
            with_failure_count: Pass the failure count to the callback when true.

        Returns:
            The operation's result.
        """

        def should_retry(error: Exception) -> bool:
            return _is_transient_redis_error(error) and (
                is_retryable is None or is_retryable(error)
            )

        if self._active.get():
            return Retry(
                NoBackoff(),
                0,
                supported_errors=RETRYABLE_REDIS_ERRORS,
            ).call_with_retry(
                do,
                fail,
                should_retry,
                with_failure_count,
            )

        token = self._active.set(True)
        try:
            return super().call_with_retry(
                do,
                fail,
                should_retry,
                with_failure_count,
            )
        finally:
            self._active.reset(token)


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


def _redis_pool(
    settings: Settings,
    host: str,
    port: int,
    max_connections: int,
    retry: Retry,
) -> ConnectionPool:
    """Construct a Redis pool with the configured transport and retry policy.

    Args:
        settings: Redis authentication and TLS settings.
        host: Validated Redis host.
        port: Validated Redis port.
        max_connections: Maximum connections in this process's pool.
        retry: redis-py retry policy for commands using the pool.

    Returns:
        Configured Redis connection pool.
    """
    if settings.redis_use_tls:
        return ConnectionPool(
            connection_class=SSLConnection,
            host=host,
            port=port,
            password=settings.redis_password,
            max_connections=max_connections,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry=retry,
            retry_on_timeout=False,
            ssl_ca_data=settings.redis_ca_cert_data,
            ssl_check_hostname=False,
            ssl_cert_reqs="required",
        )

    return ConnectionPool(
        host=host,
        port=port,
        password=settings.redis_password,
        max_connections=max_connections,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry=retry,
        retry_on_timeout=False,
    )


def session_unavailable_response(app: Flask) -> Response:
    """Create an error response without trying to save the Flask session.

    Args:
        app: Current Flask application.

    Returns:
        HTTP 500 response containing the respondent-facing error page.
    """
    response = app.make_response((render_template("session_unavailable.html"), 500))
    response.headers["Cache-Control"] = "no-store"
    return response


class SessionAwareFlask(Flask):
    """Convert response-time Redis session failures into an unsaved HTTP 500."""

    def process_response(self, response: Response) -> Response:
        """Finalise a response, handling a Redis session save failure.

        Args:
            response: Response produced by the route.

        Returns:
            Normal response, or an unsaved error response after Redis failure.
        """
        try:
            return super().process_response(response)
        except RedisError as exc:
            logger.critical(
                "Redis session operation failed operation=%s error_type=%s",
                flask_request.environ.get(SAVE_OPERATION_KEY, "response_processing"),
                type(exc).__name__,
            )
            return session_unavailable_response(self)


class AbsoluteExpiryRedisSessionInterface(RedisSessionInterface):
    """Use Flask-Session with fixed login expiry and safe read failure handling."""

    def open_session(self, app: Flask, request: Request) -> ServerSideSession:
        """Open a session without treating a failed Redis read as a new login.

        Args:
            app: Current Flask application.
            request: Request containing the existing session cookie.

        Returns:
            Loaded session, or a temporary empty session after a failed read.
        """
        try:
            return super().open_session(app, request)
        except RedisError as exc:
            logger.critical(
                "Redis session operation failed operation=get error_type=%s",
                type(exc).__name__,
            )
            request.environ[READ_FAILURE_KEY] = True
            return ServerSideSession(sid=self._generate_sid(self.sid_length))

    def save_session(
        self,
        app: Flask,
        session: SessionMixin,
        response: Response,
    ) -> None:
        """Never persist or change cookies after a failed session read.

        Args:
            app: Current Flask application.
            session: Session opened for this request.
            response: Response being finalised.

        Raises:
            TypeError: If the session is not a server-side session.
        """
        if flask_request.environ.get(READ_FAILURE_KEY):
            return

        if not isinstance(session, ServerSideSession):
            raise TypeError("Redis session interface requires a server-side session")

        super().save_session(app, session, response)

    def _delete_session(self, store_id: str) -> None:
        """Delete one Redis session, recording the operation for error handling.

        Args:
            store_id: Redis key to delete.

        Raises:
            RedisError: If Redis cannot complete the deletion.
        """
        flask_request.environ[SAVE_OPERATION_KEY] = "delete"
        super()._delete_session(store_id)

    def _upsert_session(
        self,
        session_lifetime: timedelta,
        session: ServerSideSession,
        store_id: str,
    ) -> None:
        """Write a session without extending an authenticated login deadline.

        Args:
            session_lifetime: Configured maximum lifetime.
            session: Session being saved by Flask-Session.
            store_id: Redis key assigned to this session.

        Raises:
            ValueError: If an authenticated session has an invalid login time.
            RedisError: If Redis cannot save the session.
        """
        flask_request.environ[SAVE_OPERATION_KEY] = "set"

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
        RuntimeError: If Redis is unavailable during the single startup check.
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

    if settings.redis_use_tls and (
        settings.redis_ca_cert_data is None or not settings.redis_ca_cert_data.strip()
    ):
        raise ValueError("REDIS_CA_CERT_DATA is required when REDIS_USE_TLS=true")

    startup_pool = _redis_pool(
        settings,
        host.strip(),
        port,
        max_connections,
        Retry(NoBackoff(), 0, supported_errors=RETRYABLE_REDIS_ERRORS),
    )
    try:
        try:
            available = Redis(connection_pool=startup_pool).ping()
        except RedisError as exc:
            logger.critical(
                "Redis session store unavailable at startup error_type=%s",
                type(exc).__name__,
            )
            raise RuntimeError("Redis session store unavailable at startup") from exc

        if not available:
            logger.critical("Redis session store did not acknowledge startup ping")
            raise RuntimeError("Redis session store did not acknowledge startup ping")
    finally:
        startup_pool.disconnect()

    logger.info("Redis session store available at startup")

    runtime_pool = _redis_pool(
        settings,
        host.strip(),
        port,
        max_connections,
        SessionRetry(
            NoBackoff(),
            1,
            supported_errors=RETRYABLE_REDIS_ERRORS,
        ),
    )
    redis_client = Redis(connection_pool=runtime_pool)

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
