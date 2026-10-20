"""Tests for application-wide error pages."""

from http import HTTPStatus

from flask import Flask
from flask.testing import FlaskClient


def test_internal_server_error_shows_branded_page(
    app: Flask,
) -> None:
    """Ensure the branded internal server error page is shown when an exception is raised."""
    # In development mode, Flask would normally propagate exceptions to the test client
    # meaning the error handler would not be invoked.
    # We disable this to test the error handler and check the contents of the branded error page.
    app.config["PROPAGATE_EXCEPTIONS"] = False

    # Define the text of the exception to check that it does not appear in the
    # branded error page
    exception_message = "private exception detail"

    @app.get("/test-internal-server-error")
    def error_route() -> None:
        raise RuntimeError(exception_message)

    response = app.test_client().get("/test-internal-server-error")
    page = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers["Cache-Control"] == "no-store"
    assert "Office for National Statistics" in page
    assert "The service is temporarily unavailable" in page
    assert exception_message not in page


def test_not_found_is_not_handled_as_internal_server_error(client: FlaskClient) -> None:
    """Ensure internal server error does not show for page not found errors."""
    response = client.get("/does-not-exist")
    page = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "The service is temporarily unavailable" not in page
