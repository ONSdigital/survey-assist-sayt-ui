"""Authentication decorators."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from flask import redirect, request, session, url_for
from flask.typing import ResponseReturnValue

SESSION_USER_KEY = "authenticated_user"
POST_LOGIN_REDIRECT_KEY = "post_login_redirect"

P = ParamSpec("P")
R = TypeVar("R", bound=ResponseReturnValue)


def login_required(view: Callable[P, R]) -> Callable[P, ResponseReturnValue]:
    """Require an authenticated user for the wrapped route.

    Args:
        view: Route handler to guard.

    Returns:
        Callable[P, ResponseReturnValue]: Wrapped handler that redirects
        unauthenticated requests to sign in.
    """

    @wraps(view)
    def wrapped_view(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        """Execute the wrapped view when authenticated.

        Args:
            *args: Positional arguments for the wrapped view.
            **kwargs: Keyword arguments for the wrapped view.

        Returns:
            ResponseReturnValue: Original view response, or a redirect to login.
        """
        if session.get(SESSION_USER_KEY):
            return cast(ResponseReturnValue, view(*args, **kwargs))
        if request.method == "GET":
            session[POST_LOGIN_REDIRECT_KEY] = request.full_path.rstrip("?")
        return redirect(url_for("auth.login"))

    return wrapped_view
