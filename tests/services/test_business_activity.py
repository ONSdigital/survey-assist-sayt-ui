"""Test the business activity search service."""

from __future__ import annotations

from http import HTTPStatus

import httpx
import pytest

from survey_assist_sayt_ui.services.business_activity import (
    BusinessActivityApiError,
    HttpBusinessActivitySearchClient,
)


def test_search_uses_current_bearer_token() -> None:
    """Use the latest configured JWT on each request."""
    authorization_headers: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        authorization_headers.append(request.headers["Authorization"])
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json=[{"en": "81210 - General cleaning of buildings"}],
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handle_request))
    client = HttpBusinessActivitySearchClient(
        endpoint_url="https://gateway.example/sic-lookup",
        token="initial-token",
        client=http_client,
    )

    client.search("cleaning", limit=20)
    client.update_token("refreshed-token")
    client.search("cleaning", limit=20)

    assert authorization_headers == [
        "Bearer initial-token",
        "Bearer refreshed-token",
    ]

    client.close()


def test_search_refreshes_token_and_retries_once_after_unauthorized() -> None:
    """Test that a 401 refreshes the JWT and retries the request once."""
    request_authorizations: list[str | None] = []
    token_refresh_count = 0

    def token_refresher() -> str:
        nonlocal token_refresh_count
        token_refresh_count += 1
        return "new-jwt-token"

    def handler(request: httpx.Request) -> httpx.Response:
        request_authorizations.append(request.headers.get("Authorization"))

        if len(request_authorizations) == 1:
            return httpx.Response(HTTPStatus.UNAUTHORIZED, request=request)

        return httpx.Response(
            HTTPStatus.OK,
            json={"results": [{"en": "Car repair", "code": "45200"}]},
            request=request,
        )

    client = HttpBusinessActivitySearchClient(
        endpoint_url="https://example.com/sic-lookup",
        token="expired-jwt-token",
        query_parameter="description",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        token_refresher=token_refresher,
    )

    suggestions = client.search("car", limit=10)

    assert token_refresh_count == 1
    assert request_authorizations == [
        "Bearer expired-jwt-token",
        "Bearer new-jwt-token",
    ]
    assert len(suggestions) == 1
    assert suggestions[0].label == "Car repair"
    assert suggestions[0].code == "45200"


def test_search_does_not_refresh_token_for_non_unauthorized_error() -> None:
    """Test that only 401 responses trigger JWT refresh."""

    def token_refresher() -> str:
        pytest.fail("Token refresher should not be called for non-401 errors")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            request=request,
        )

    client = HttpBusinessActivitySearchClient(
        endpoint_url="https://example.com/sic-lookup",
        token="current-jwt-token",
        query_parameter="description",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        token_refresher=token_refresher,
    )

    with pytest.raises(BusinessActivityApiError, match="Business activity API request failed"):
        client.search("car", limit=10)


def test_search_raises_error_when_retry_after_token_refresh_is_still_unauthorized() -> None:
    """Test that repeated 401 responses do not cause an infinite retry loop."""
    request_authorizations: list[str | None] = []

    def token_refresher() -> str:
        return "new-jwt-token"

    def handler(request: httpx.Request) -> httpx.Response:
        request_authorizations.append(request.headers.get("Authorization"))
        return httpx.Response(HTTPStatus.UNAUTHORIZED, request=request)

    client = HttpBusinessActivitySearchClient(
        endpoint_url="https://example.com/sic-lookup",
        token="expired-jwt-token",
        query_parameter="description",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        token_refresher=token_refresher,
    )

    with pytest.raises(BusinessActivityApiError, match="Business activity API request failed"):
        client.search("car", limit=10)

    assert request_authorizations == [
        "Bearer expired-jwt-token",
        "Bearer new-jwt-token",
    ]
