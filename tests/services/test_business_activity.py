from __future__ import annotations

import httpx

from survey_assist_sayt_ui.services.business_activity import (
    HttpBusinessActivitySearchClient,
)


def test_search_uses_current_bearer_token() -> None:
    """Use the latest configured JWT on each request."""
    authorization_headers: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        authorization_headers.append(request.headers["Authorization"])
        return httpx.Response(
            status_code=200,
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
