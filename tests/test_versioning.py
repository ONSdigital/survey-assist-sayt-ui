"""Tests for application version resolution."""

from importlib.metadata import PackageNotFoundError

import pytest

from survey_assist_sayt_ui import versioning


def test_get_app_version_prefers_image_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that image metadata takes precedence."""
    monkeypatch.setenv("APP_VERSION", "1.2.3")

    assert versioning.get_app_version() == "1.2.3"


def test_get_app_version_uses_installed_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the local-development package metadata fallback."""
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setattr(versioning, "version", lambda package_name: "0.1.0")

    assert versioning.get_app_version() == "0.1.0"


def test_get_app_version_returns_unknown_when_package_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the fallback when no image or package version is available."""

    def raise_package_not_found(package_name: str) -> str:
        """Raise an error for missing package metadata."""
        raise PackageNotFoundError(package_name)

    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setattr(versioning, "version", raise_package_not_found)

    assert versioning.get_app_version() == "0.0.0+unknown"
