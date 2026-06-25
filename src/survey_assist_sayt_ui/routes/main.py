"""Main UI routes."""

from __future__ import annotations

import logging
from typing import cast

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask.typing import ResponseReturnValue

from survey_assist_sayt_ui.auth.decorators import SESSION_USER_KEY, login_required
from survey_assist_sayt_ui.services.business_activity import (
    BusinessActivityApiError,
    BusinessActivityApiTimeoutError,
    BusinessActivitySearchClient,
)

MIN_AUTOSUGGEST_CHARACTERS = 3
MAX_AUTOSUGGEST_QUERY_LENGTH = 200
MAX_AUTOSUGGEST_RESULTS = 20

logger = logging.getLogger(__name__)

main_blueprint = Blueprint("main", __name__)


@main_blueprint.get("/")
@login_required
def index() -> ResponseReturnValue:
    """Render the protected landing page.

    Returns:
        ResponseReturnValue: Home page template response.
    """
    return render_template(
        "index.html",
        page_title="Home",
        authenticated_user=session.get(SESSION_USER_KEY),
    )


@main_blueprint.get("/standard-autosuggest")
@login_required
def standard_autosuggest() -> ResponseReturnValue:
    """Render the protected autosuggest page.

    Returns:
        ResponseReturnValue: Autosuggest page template response.
    """
    return render_template(
        "business_activity.html",
        business_activity="",
        business_activity_not_listed=False,
        error_message=None,
        page_title="Standard business activity",
        authenticated_user=session.get(SESSION_USER_KEY),
    )


@main_blueprint.get("/api-autosuggest")
@login_required
def api_autosuggest() -> ResponseReturnValue:
    """Render the protected API autosuggest page.

    Returns:
        ResponseReturnValue: Autosuggest page template response.
    """
    return render_template(
        "business_activity_api.html",
        business_activity="",
        business_activity_not_listed=False,
        error_message=None,
        page_title="API business activity",
        authenticated_user=session.get(SESSION_USER_KEY),
    )


@main_blueprint.get("/api/business-activity-suggestions")
@login_required
def business_activity_suggestions() -> ResponseReturnValue:
    """Proxy business activity searches to the configured API."""
    query = request.args.get("q", "", type=str).strip()

    if len(query) < MIN_AUTOSUGGEST_CHARACTERS:
        return jsonify([])

    if len(query) > MAX_AUTOSUGGEST_QUERY_LENGTH:
        return {"error": "Search query is too long"}, 400

    client = cast(
        BusinessActivitySearchClient,
        current_app.extensions["business_activity_search_client"],
    )

    try:
        suggestions = client.search(
            query,
            limit=MAX_AUTOSUGGEST_RESULTS,
        )
    except BusinessActivityApiTimeoutError:
        logger.warning(
            "Business activity API request timed out",
            extra={"query_length": len(query)},
        )
        return {"error": "Suggestion service timed out"}, 504
    except BusinessActivityApiError:
        logger.exception(
            "Business activity API request failed",
            extra={"query_length": len(query)},
        )
        return {"error": "Suggestion service unavailable"}, 502

    return jsonify([suggestion.to_dict() for suggestion in suggestions])


@main_blueprint.route("/save-response", methods=["POST"])
@login_required
def save_response() -> ResponseReturnValue:
    """Saves the response to the selection.

    Returns:
        ResponseReturnValue: Redirect or error response.
    """
    selected = request.form.get("business_activity")

    return render_template(
        "confirmation.html",
        page_title="Confirmation",
        selected=selected,
        authenticated_user=session.get(SESSION_USER_KEY),
    )


@main_blueprint.get("/cookies")
def cookies() -> ResponseReturnValue:
    """Render the cookies page.

    Returns:
        ResponseReturnValue: Cookies page template response.
    """
    return render_template("cookies.html", page_title="Cookies")


@main_blueprint.get("/accessibility")
def accessibility() -> ResponseReturnValue:
    """Render the accessibility statement page.

    Returns:
        ResponseReturnValue: Accessibility statement template response.
    """
    return render_template("accessibility.html", page_title="Accessibility statement")


@main_blueprint.get("/privacy")
def privacy() -> ResponseReturnValue:
    """Render the privacy notice page.

    Returns:
        ResponseReturnValue: Privacy notice template response.
    """
    return render_template("privacy.html", page_title="Privacy notice")


@main_blueprint.get("/health")
def health() -> ResponseReturnValue:
    """Provide a basic health check response.

    Returns:
        ResponseReturnValue: JSON payload indicating service health.
    """
    return {"status": "ok"}
