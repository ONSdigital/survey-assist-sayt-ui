"""Application version helpers for the Survey Assist SAYT UI.

This module provides a helper to retrieve the installed package version for the
UI, using the package name defined in pyproject.toml.
"""

from importlib.metadata import PackageNotFoundError, version
import os

PACKAGE_NAME = "survey-assist-sayt-ui"
UNKNOWN_VERSION = "0.0.0+unknown"


def get_app_version() -> str:
    """Return the configured or installed application version.

    Returns:
        str: Application version or a fallback value when it cannot be
            determined.
    """
    image_version = os.getenv("APP_VERSION")

    if image_version:
        return image_version

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return UNKNOWN_VERSION
