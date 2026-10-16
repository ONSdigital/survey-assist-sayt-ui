"""Tests for browser context configuration."""

import pytest


def test_browser_context_has_no_authorization_without_token(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.delenv("TEST_E2E_BEARER_TOKEN", raising=False)
    context_args = request.getfixturevalue("browser_context_args")
    assert "Authorization" not in context_args.get("extra_http_headers", {})


def test_browser_context_uses_bearer_token(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("TEST_E2E_BEARER_TOKEN", "test-token")
    context_args = request.getfixturevalue("browser_context_args")
    assert context_args["extra_http_headers"]["Authorization"] == "Bearer test-token"
