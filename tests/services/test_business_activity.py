"""Test the business activity search service."""

from __future__ import annotations

from http import HTTPStatus
import json

import httpx
import pytest

from survey_assist_sayt_ui.services.business_activity import (
    BusinessActivityApiError,
    BusinessActivityApiTimeoutError,
    HttpBusinessActivitySearchClient,
)
from survey_assist_sayt_ui.services.survey_assist_api import SurveyAssistApiClient


def _create_client(
    handler: httpx.MockTransport,
) -> HttpBusinessActivitySearchClient:
    """Create a business activity client using a mocked HTTP transport."""
    api_client = SurveyAssistApiClient(
        base_url="https://gateway.example",
        token="test-jwt-token",
        client=httpx.Client(transport=handler),
    )

    return HttpBusinessActivitySearchClient(api_client=api_client)


def test_search_posts_suggestions_request() -> None:
    """Test that searches use the Survey Assist suggestions endpoint."""
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(
            HTTPStatus.OK,
            json={"suggestions": []},
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    client.search("soft", limit=5)

    assert captured_request is not None
    assert captured_request.method == "POST"
    assert captured_request.url == "https://gateway.example/suggestions"
    assert json.loads(captured_request.content) == {
        "type": "sic",
        "query": "soft",
        "limit": 5,
    }


def test_search_maps_suggestions_response() -> None:
    """Test that API suggestions are mapped to business activity suggestions."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={
                "suggestions": [
                    {
                        "display_text": "Toy and game manufacturing: 32409",
                    },
                    {
                        "display_text": "Soft drinks production: 11070",
                    },
                    {
                        "display_text": "Landscape gardening: 81300",
                    },
                ]
            },
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    suggestions = client.search("soft", limit=5)

    assert [suggestion.label for suggestion in suggestions] == [
        "Toy and game manufacturing: 32409",
        "Soft drinks production: 11070",
        "Landscape gardening: 81300",
    ]


def test_search_ignores_optional_score() -> None:
    """Test that optional API scores do not affect displayed suggestions."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={
                "suggestions": [
                    {
                        "display_text": "Software development: 62012",
                        "score": 0.95,
                    }
                ]
            },
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    suggestions = client.search("software", limit=5)

    assert len(suggestions) == 1
    assert suggestions[0].label == "Software development: 62012"


def test_search_raises_error_for_invalid_response() -> None:
    """Test that an invalid suggestions response raises an API error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={
                "suggestions": [
                    {
                        "unexpected_field": "Software development",
                    }
                ]
            },
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(
        BusinessActivityApiError,
        match="Business activity API request failed",
    ):
        client.search("software", limit=5)


def test_search_raises_error_for_invalid_json() -> None:
    """Test that invalid response JSON raises an API error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            content=b"not-json",
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(
        BusinessActivityApiError,
        match="Business activity API request failed",
    ):
        client.search("software", limit=5)


def test_search_raises_error_for_api_failure() -> None:
    """Test that Survey Assist API failures are translated."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(
        BusinessActivityApiError,
        match="Business activity API request failed",
    ):
        client.search("software", limit=5)


def test_search_raises_timeout_error() -> None:
    """Test that Survey Assist API timeouts are translated."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Request timed out",
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(
        BusinessActivityApiTimeoutError,
        match="Business activity API request timed out",
    ):
        client.search("software", limit=5)
