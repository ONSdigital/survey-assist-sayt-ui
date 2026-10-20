"""Shared responses for application errors."""

from flask import Flask, Response, render_template


def internal_server_error_response(app: Flask) -> Response:
    """Build the response for an internal server error."""
    response = app.make_response((render_template("500.html"), 500))
    response.headers["Cache-Control"] = "no-store"
    return response
