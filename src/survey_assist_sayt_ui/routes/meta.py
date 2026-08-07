"""Application metadata routes for the Survey Assist SAYT UI."""

from __future__ import annotations

import os

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

from survey_assist_sayt_ui.versioning import get_app_version

meta_blueprint = Blueprint("meta", __name__)


@meta_blueprint.get("/__meta")
def meta() -> ResponseReturnValue:
    """Return application build and Cloud Run metadata.

    Returns:
        ResponseReturnValue: JSON response containing deployment metadata.
    """
    return jsonify(
        {
            "app_version": get_app_version(),
            "git_sha": os.getenv("APP_GIT_SHA", "unknown"),
            "build_date": os.getenv("APP_BUILD_DATE", "unknown"),
            "service": os.getenv("K_SERVICE", "unknown"),
            "revision": os.getenv("K_REVISION", "unknown"),
            "configuration": os.getenv("K_CONFIGURATION", "unknown"),
            "runtime": "cloud-run",
        }
    )
