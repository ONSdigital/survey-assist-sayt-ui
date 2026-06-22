"""Authentication routes."""

from __future__ import annotations

from http import HTTPStatus
from typing import cast

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

from .decorators import POST_LOGIN_REDIRECT_KEY, SESSION_USER_KEY
from .service import AuthService

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.get("/login")
def login() -> ResponseReturnValue:
    """Render the sign-in page.

    Returns:
        ResponseReturnValue: Login template response, or redirect for
        already-authenticated users.
    """
    if session.get(SESSION_USER_KEY):
        return redirect(url_for("main.index"))
    return render_template(
        "login.html", page_title="Sign in", contact_email="example@ons.gov.uk", errors=[]
    )


@auth_blueprint.post("/check-login")
def check_login() -> ResponseReturnValue:
    """Validate credentials and establish a session.

    Returns:
        ResponseReturnValue: Redirect on success, or the login template with
        an HTTP error status when validation fails.
    """
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""

    if not username or not password:
        return (
            render_template(
                "login.html",
                page_title="Sign in",
                contact_email="example@ons.gov.uk",
                errors=["Enter your email address and password."],
                username=username,
            ),
            HTTPStatus.BAD_REQUEST,
        )

    auth_service = cast(AuthService, current_app.config["auth_service"])
    if not auth_service.credentials_match(username, password):
        return (
            render_template(
                "login.html",
                page_title="Sign in",
                contact_email="example@ons.gov.uk",
                errors=["Invalid email address or password."],
                username=username,
            ),
            HTTPStatus.UNAUTHORIZED,
        )

    session[SESSION_USER_KEY] = username
    redirect_target = session.pop(POST_LOGIN_REDIRECT_KEY, url_for("main.index"))
    return redirect(str(redirect_target))


@auth_blueprint.get("/logout")
def logout() -> ResponseReturnValue:
    """Clear the authenticated session.

    Returns:
        ResponseReturnValue: Redirect response to the login page.
    """
    session.clear()
    return redirect(url_for("auth.login"))
