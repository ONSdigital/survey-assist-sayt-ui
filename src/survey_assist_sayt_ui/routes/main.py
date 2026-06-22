"""Main UI routes."""

from __future__ import annotations

from flask import Blueprint, render_template, request, session
from flask.typing import ResponseReturnValue

from survey_assist_sayt_ui.auth.decorators import SESSION_USER_KEY, login_required

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
        page_title="Business activity",
        authenticated_user=session.get(SESSION_USER_KEY),
    )


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
