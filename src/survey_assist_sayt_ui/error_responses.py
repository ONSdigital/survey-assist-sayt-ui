"""Shared responses for application errors."""

from flask import Flask, Response, render_template


def _error_response(app: Flask, status: int) -> Response:
    response = app.make_response((render_template(f"{status}.html"), status))
    response.headers["Cache-Control"] = "no-store"
    return response


def not_found_response(app: Flask) -> Response:
    """Build the response for a page not found error."""
    return _error_response(app, 404)


def internal_server_error_response(app: Flask) -> Response:
    """Build the response for an internal server error."""
    return _error_response(app, 500)
