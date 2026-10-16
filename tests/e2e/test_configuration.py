"""Tests for browser context configuration."""

import pytest


def test_browser_context_uses_bearer_token(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Ensure the Authorization header is set when a bearer token environment variable is set."""
    monkeypatch.setenv("TEST_E2E_BEARER_TOKEN", "test-token")
    context_args = request.getfixturevalue("browser_context_args")
    assert context_args["extra_http_headers"]["Authorization"] == "Bearer test-token"
