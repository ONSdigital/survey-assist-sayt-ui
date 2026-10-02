"""Tests for configurable Flask session storage."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
import logging
from math import ceil

from flask import Flask
from flask.sessions import SecureCookieSessionInterface
from flask.testing import FlaskClient
from flask_session.redis import RedisSessionInterface
import msgspec
import pytest
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from survey_assist_sayt_ui import session_handler
from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_RESULT_USER_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.auth.session_lifetime import login_deadline
from survey_assist_sayt_ui.config import Settings, load_settings
from survey_assist_sayt_ui.survey.session import (
    SURVEY_FEEDBACK_RESPONSES_KEY,
    SURVEY_RESPONSE_START_TIME_KEY,
    SURVEY_RESPONSES_KEY,
)

TokenRefresher = Callable[[int, str, str, str], tuple[int, str]]


@pytest.fixture(name="redis_store")
def redis_store_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, bytes]:
    """Provide an in-memory store behind the Redis commands Flask-Session uses."""
    stored_values: dict[str, bytes] = {}

    def ping(_client: Redis) -> bool:
        """Acknowledge the application startup check."""
        return True

    def get(_client: Redis, name: str) -> bytes | None:
        """Retrieve a serialized session."""
        return stored_values.get(name)

    def set_value(
        _client: Redis,
        name: str,
        value: bytes,
        ex: int | None = None,
        exat: int | None = None,
    ) -> bool:
        """Store a session with either a relative or absolute expiry."""
        assert (ex is None) != (exat is None)
        if ex is not None:
            assert ex > 0
        if exat is not None:
            assert exat > 0
        stored_values[name] = value
        return True

    def delete(_client: Redis, name: str) -> int:
        """Delete a serialized session."""
        return int(stored_values.pop(name, None) is not None)

    monkeypatch.setattr(Redis, "ping", ping)
    monkeypatch.setattr(Redis, "get", get)
    monkeypatch.setattr(Redis, "set", set_value)
    monkeypatch.setattr(Redis, "delete", delete)

    return stored_values


@pytest.fixture(name="redis_app")
def redis_app_fixture(
    app: Flask,
    redis_store: dict[str, bytes],
    static_token_refresher: TokenRefresher,
) -> Flask:
    """Create the existing application with Redis session storage."""
    assert redis_store == {}

    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    application = create_app(
        settings=replace(
            settings,
            session_backend="redis",
            redis_host="localhost",
        ),
        auth_service=app.config["auth_service"],
        survey_definition=app.extensions["survey_definition"],
        token_refresher=static_token_refresher,
    )
    application.config.update(TESTING=True)

    return application


def test_load_settings_defaults_to_client_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep client-side sessions when no backend is configured."""
    monkeypatch.setenv(
        "SURVEY_ASSIST_API_BASE_URL",
        "http://0.0.0.0:8080/v1/survey-assist",
    )
    monkeypatch.setenv(
        "SA_EMAIL",
        "sayt-ui@example.iam.gserviceaccount.com",
    )
    monkeypatch.delenv("SESSION_BACKEND", raising=False)

    assert load_settings().session_backend == "client"


def test_load_settings_normalises_redis_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read the selected backend and Redis connection settings."""
    monkeypatch.setenv(
        "SURVEY_ASSIST_API_BASE_URL",
        "http://0.0.0.0:8080/v1/survey-assist",
    )
    monkeypatch.setenv(
        "SA_EMAIL",
        "sayt-ui@example.iam.gserviceaccount.com",
    )
    monkeypatch.setenv("SESSION_BACKEND", " ReDiS ")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "12")

    settings = load_settings()

    assert settings.session_backend == "redis"
    assert settings.redis_host == "localhost"
    assert settings.redis_port == "6380"
    assert settings.redis_max_connections == "12"


def test_client_backend_preserves_flask_session_interface(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client mode must not construct a Redis pool or replace Flask sessions."""
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    def unexpected_redis_connection(**_kwargs: object) -> None:
        """Fail if client mode attempts to configure Redis."""
        pytest.fail("Client-side sessions must not connect to Redis")

    monkeypatch.setattr(
        session_handler,
        "ConnectionPool",
        unexpected_redis_connection,
    )

    session_handler.configure_session(
        app,
        replace(
            settings,
            session_backend="client",
            redis_host=None,
            redis_port="not-a-port",
        ),
    )

    assert isinstance(app.session_interface, SecureCookieSessionInterface)


def test_redis_backend_configures_flask_session(
    redis_app: Flask,
) -> None:
    """Install the Redis interface with msgpack and a bounded pool."""
    assert isinstance(redis_app.session_interface, RedisSessionInterface)
    assert redis_app.config["SESSION_TYPE"] == "redis"
    assert redis_app.config["SESSION_SERIALIZATION_FORMAT"] == "msgpack"
    assert redis_app.config["SESSION_KEY_PREFIX"] == "sayt-ui:session:"
    assert redis_app.config["SESSION_PERMANENT"] is False
    assert redis_app.config["SESSION_REFRESH_EACH_REQUEST"] is False

    redis_client = redis_app.config["SESSION_REDIS"]
    assert isinstance(redis_client, Redis)
    assert redis_client.connection_pool.max_connections == 32
    assert redis_client.connection_pool.connection_kwargs["host"] == "localhost"
    assert redis_client.connection_pool.connection_kwargs["port"] == 6379
    assert redis_client.connection_pool.connection_kwargs["socket_connect_timeout"] == 5
    assert redis_client.connection_pool.connection_kwargs["socket_timeout"] == 5


def test_invalid_backend_fails_configuration(
    app: Flask,
) -> None:
    """Reject unsupported backends instead of silently using client sessions."""
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    with pytest.raises(
        ValueError,
        match="SESSION_BACKEND must be 'client' or 'redis'",
    ):
        session_handler.configure_session(
            app,
            replace(settings, session_backend="unknown"),
        )


@pytest.mark.parametrize("redis_host", [None, "", "  "])
def test_redis_backend_requires_host(
    app: Flask,
    redis_host: str | None,
) -> None:
    """Reject an absent or blank Redis host at startup."""
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    with pytest.raises(
        ValueError,
        match="REDIS_HOST is required when SESSION_BACKEND=redis",
    ):
        session_handler.configure_session(
            app,
            replace(
                settings,
                session_backend="redis",
                redis_host=redis_host,
            ),
        )


@pytest.mark.parametrize(
    ("setting_name", "value", "error"),
    [
        ("redis_port", "invalid", "REDIS_PORT must be an integer"),
        ("redis_port", "0", "REDIS_PORT must be between 1 and 65535"),
        ("redis_port", "65536", "REDIS_PORT must be between 1 and 65535"),
        (
            "redis_max_connections",
            "invalid",
            "REDIS_MAX_CONNECTIONS must be an integer",
        ),
        (
            "redis_max_connections",
            "0",
            "REDIS_MAX_CONNECTIONS must be between 1 and unbounded",
        ),
    ],
)
def test_redis_backend_rejects_invalid_connection_settings(
    app: Flask,
    setting_name: str,
    value: str,
    error: str,
) -> None:
    """Validate Redis settings before attempting a connection."""
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    with pytest.raises(ValueError, match=error):
        session_handler.configure_session(
            app,
            replace(
                settings,
                session_backend="redis",
                redis_host="localhost",
                **{setting_name: value},
            ),
        )


def test_redis_backend_fails_app_startup_when_ping_raises(
    app: Flask,
    redis_store: dict[str, bytes],
    static_token_refresher: TokenRefresher,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Abort application creation when the Redis store cannot be reached."""
    assert redis_store == {}
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    def unavailable(_client: Redis) -> bool:
        """Simulate an unavailable Redis server."""
        raise RedisConnectionError("Redis unavailable")

    monkeypatch.setattr(Redis, "ping", unavailable)

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(
            RuntimeError,
            match="Redis session store unavailable at startup",
        ):
            create_app(
                settings=replace(
                    settings,
                    session_backend="redis",
                    redis_host="localhost",
                ),
                auth_service=app.config["auth_service"],
                survey_definition=app.extensions["survey_definition"],
                token_refresher=static_token_refresher,
            )

    assert "Redis session store unavailable at startup" in caplog.text


def test_redis_backend_fails_when_ping_is_not_acknowledged(
    app: Flask,
    redis_store: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not start when Redis does not acknowledge its health check."""
    assert redis_store == {}
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    monkeypatch.setattr(Redis, "ping", lambda _client: False)

    with pytest.raises(
        RuntimeError,
        match="Redis session store did not acknowledge startup ping",
    ):
        session_handler.configure_session(
            Flask(__name__),
            replace(
                settings,
                session_backend="redis",
                redis_host="localhost",
            ),
        )


def test_redis_session_round_trip_preserves_existing_survey_data(
    redis_app: Flask,
    redis_store: dict[str, bytes],
) -> None:
    """Save and reload authentication, survey and feedback via flask.session."""
    client = redis_app.test_client()
    login_time = datetime.now(UTC).isoformat()
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_RESULT_USER_KEY] = "11-01"
        flask_session[SESSION_LOGIN_TIME_KEY] = login_time
        flask_session[SURVEY_RESPONSE_START_TIME_KEY] = "2026-09-25T09:05:00+00:00"
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q-about-you": {
                "question_name": "about_you_question",
                "values": {
                    "first-name": "Alex",
                    "middle-names": "",
                    "surname": "Smith",
                },
            }
        }
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq1": {
                "question_name": "survey_ease_question",
                "response_name": "survey-ease",
                "value": "easy",
            }
        }

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "25-34"},
    )
    assert response.status_code == HTTPStatus.FOUND

    cookie_name = redis_app.config["SESSION_COOKIE_NAME"]
    cookie = client.get_cookie(cookie_name)
    assert cookie is not None
    assert "person@example.com" not in cookie.value
    assert "25-34" not in cookie.value

    store_key = f"sayt-ui:session:{cookie.value}"
    assert store_key in redis_store

    stored = msgspec.msgpack.decode(redis_store[store_key])
    assert stored[SESSION_USER_KEY] == "person@example.com"
    assert stored[SESSION_RESULT_USER_KEY] == "11-01"
    assert stored[SESSION_LOGIN_TIME_KEY] == login_time
    assert stored[SURVEY_RESPONSE_START_TIME_KEY] == "2026-09-25T09:05:00+00:00"
    assert stored[SURVEY_RESPONSES_KEY]["q0"] == {
        "question_name": "age_range_question",
        "response_name": "age-range",
        "value": "25-34",
    }
    assert stored[SURVEY_RESPONSES_KEY]["q-about-you"]["values"] == {
        "first-name": "Alex",
        "middle-names": "",
        "surname": "Smith",
    }
    assert stored[SURVEY_FEEDBACK_RESPONSES_KEY]["fq1"]["value"] == "easy"

    another_client = redis_app.test_client()
    another_client.set_cookie(cookie_name, cookie.value)

    response = another_client.get("/survey/questions/q0")
    assert response.status_code == HTTPStatus.OK

    with another_client.session_transaction() as flask_session:
        assert flask_session[SESSION_USER_KEY] == "person@example.com"
        assert flask_session[SURVEY_RESPONSES_KEY]["q0"]["value"] == "25-34"
        assert flask_session[SURVEY_RESPONSES_KEY]["q-about-you"]["values"]["first-name"] == "Alex"
        assert flask_session[SURVEY_FEEDBACK_RESPONSES_KEY]["fq1"]["value"] == "easy"


def test_login_deadline_is_fixed_at_exactly_fifteen_days() -> None:
    """Do not extend the deadline when later requests occur."""
    started = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

    assert login_deadline(
        started.isoformat(),
        timedelta(days=15),
    ) == datetime(2026, 10, 16, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize("login_time", [None, "", "invalid", "2026-10-01T10:00:00"])
def test_login_deadline_rejects_invalid_timestamps(login_time: object) -> None:
    """Reject incomplete authenticated sessions."""
    with pytest.raises(ValueError):
        login_deadline(login_time, timedelta(days=15))


@pytest.mark.parametrize("days", ["0", "-1", "invalid"])
def test_session_lifetime_rejects_invalid_days(
    app: Flask,
    days: str,
) -> None:
    """Validate lifetime in client mode as well as Redis mode."""
    settings = app.config["settings"]
    assert isinstance(settings, Settings)

    with pytest.raises(ValueError, match="SESSION_LIFETIME_DAYS"):
        session_handler.configure_session(
            Flask(__name__),
            replace(settings, session_lifetime_days=days),
        )


def test_client_session_expires_at_login_deadline(client: FlaskClient) -> None:
    """Remove an expired signed client session before serving protected content."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = (datetime.now(UTC) - timedelta(days=16)).isoformat()
        flask_session[SURVEY_RESPONSES_KEY] = {"q0": {"value": "old answer"}}

    response = client.get("/survey/questions/q0")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as flask_session:
        assert SESSION_USER_KEY not in flask_session
        assert SURVEY_RESPONSES_KEY not in flask_session


def test_redis_writes_keep_original_absolute_deadline(
    redis_app: Flask,
    redis_store: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saving another answer must not renew the Redis record's expiry."""
    deadlines: list[int] = []
    original_set = Redis.set

    def record_set(
        redis_client: Redis,
        name: str,
        value: bytes,
        ex: int | None = None,
        exat: int | None = None,
    ) -> bool:
        """Record an absolute expiry and pass the write to the stub store."""
        if exat is not None:
            deadlines.append(exat)
        return original_set(redis_client, name, value, ex=ex, exat=exat)

    monkeypatch.setattr(Redis, "set", record_set)
    client = redis_app.test_client()
    started = datetime.now(UTC) - timedelta(days=14)

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = started.isoformat()

    first = client.post("/survey/questions/q0", data={"age-range": "25-34"})
    assert first.status_code == HTTPStatus.FOUND
    second = client.post("/survey/questions/q1", data={"job-title": "Teacher"})
    assert second.status_code == HTTPStatus.FOUND

    assert len(deadlines) >= 3
    assert set(deadlines) == {ceil((started + timedelta(days=15)).timestamp())}
    assert redis_store


def test_redis_completion_deletes_record_and_cookie(
    redis_app: Flask,
    redis_store: dict[str, bytes],
) -> None:
    """Render completion before removing the respondent's Redis session."""
    client = redis_app.test_client()
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()
        flask_session[SURVEY_RESPONSES_KEY] = {"q0": {"value": "25-34"}}

    cookie = client.get_cookie(redis_app.config["SESSION_COOKIE_NAME"])
    assert cookie is not None
    key = f"sayt-ui:session:{cookie.value}"
    assert key in redis_store

    response = client.get("/survey/complete")

    assert response.status_code == HTTPStatus.OK
    assert "Survey complete" in response.get_data(as_text=True)
    assert key not in redis_store
    assert client.get_cookie(redis_app.config["SESSION_COOKIE_NAME"]) is None
    assert client.get("/survey/complete").status_code == HTTPStatus.FOUND


def test_redis_logout_deletes_record_and_cookie(
    redis_app: Flask,
    redis_store: dict[str, bytes],
) -> None:
    """Remove the respondent's Redis session and browser cookie on logout."""
    client = redis_app.test_client()

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    cookie_name = redis_app.config["SESSION_COOKIE_NAME"]
    cookie = client.get_cookie(cookie_name)
    assert cookie is not None

    key = f"sayt-ui:session:{cookie.value}"
    assert key in redis_store

    response = client.get("/logout")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/login")
    assert key not in redis_store
    assert client.get_cookie(cookie_name) is None


def test_redis_logout_only_clears_current_respondent_session(
    redis_app: Flask,
    redis_store: dict[str, bytes],
) -> None:
    """Clearing one Redis session must not affect another respondent."""
    first_client = redis_app.test_client()
    second_client = redis_app.test_client()

    with first_client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "first@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    with second_client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "second@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "35-44",
            }
        }

    cookie_name = redis_app.config["SESSION_COOKIE_NAME"]

    first_cookie = first_client.get_cookie(cookie_name)
    second_cookie = second_client.get_cookie(cookie_name)

    assert first_cookie is not None
    assert second_cookie is not None
    assert first_cookie.value != second_cookie.value

    first_key = f"sayt-ui:session:{first_cookie.value}"
    second_key = f"sayt-ui:session:{second_cookie.value}"

    assert first_key in redis_store
    assert second_key in redis_store

    response = first_client.get("/logout")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/login")

    assert first_key not in redis_store
    assert first_client.get_cookie(cookie_name) is None

    assert second_key in redis_store
    assert second_client.get_cookie(cookie_name) is not None

    response = second_client.get("/survey/questions/q0")

    assert response.status_code == HTTPStatus.OK

    with second_client.session_transaction() as flask_session:
        assert flask_session[SESSION_USER_KEY] == "second@example.com"
        assert flask_session[SURVEY_RESPONSES_KEY]["q0"]["value"] == "35-44"
