"""Main UI routes."""

from __future__ import annotations

from flask import Blueprint, render_template, session
from flask.typing import ResponseReturnValue

from ons_flask_auth_template.auth.decorators import SESSION_USER_KEY, login_required

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
