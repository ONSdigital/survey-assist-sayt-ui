"""Tests for the application metadata route."""

from http import HTTPStatus

from flask.testing import FlaskClient
import pytest


def test_meta_returns_application_and_cloud_run_metadata(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the metadata endpoint returns deployment information."""
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("APP_GIT_SHA", "9eca09c")
    monkeypatch.setenv("APP_BUILD_DATE", "2026-05-14T15:09:55Z")
    monkeypatch.setenv("K_SERVICE", "sayt-ui")
    monkeypatch.setenv("K_REVISION", "sayt-ui-00030-6bj")
    monkeypatch.setenv("K_CONFIGURATION", "sayt-ui")

    response = client.get("/__meta")

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {
        "app_version": "0.1.0",
        "build_date": "2026-05-14T15:09:55Z",
        "configuration": "sayt-ui",
        "git_sha": "9eca09c",
        "revision": "sayt-ui-00030-6bj",
        "runtime": "cloud-run",
        "service": "sayt-ui",
    }


def test_meta_returns_unknown_for_missing_deployment_metadata(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test metadata fallbacks outside a deployed Cloud Run revision."""
    monkeypatch.setenv("APP_VERSION", "0.1.0")

    for variable in (
        "APP_GIT_SHA",
        "APP_BUILD_DATE",
        "K_SERVICE",
        "K_REVISION",
        "K_CONFIGURATION",
    ):
        monkeypatch.delenv(variable, raising=False)

    response = client.get("/__meta")

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {
        "app_version": "0.1.0",
        "build_date": "unknown",
        "configuration": "unknown",
        "git_sha": "unknown",
        "revision": "unknown",
        "runtime": "cloud-run",
        "service": "unknown",
    }
