"""Client for retrieving business activity suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


class BusinessActivityApiError(RuntimeError):
    """Raised when the business activity API cannot be used."""


class BusinessActivityApiTimeoutError(BusinessActivityApiError):
    """Raised when the business activity API times out."""


@dataclass(frozen=True, slots=True)
class BusinessActivitySuggestion:
    """A business activity suggestion returned by the API."""

    label: str
    code: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert the suggestion to the ONS language-keyed format."""
        result = {"en": self.label}

        if self.code:
            result["code"] = self.code

        return result


class BusinessActivitySearchClient(Protocol):  # pylint: disable=too-few-public-methods
    """Interface for business activity search implementations."""

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Search for matching business activities."""


class HttpBusinessActivitySearchClient:
    """HTTP implementation of the business activity search client."""

    def __init__(
        self,
        endpoint_url: str,
        token: str,
        *,
        query_parameter: str = "q",
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not endpoint_url:
            raise ValueError("SAYT_API_URL must be configured")

        if not token:
            raise ValueError("SAYT API JWT must be configured")

        self._endpoint_url = endpoint_url
        self._query_parameter = query_parameter
        self._token = token
        self._client = (
            client
            if client is not None
            else httpx.Client(
                timeout=httpx.Timeout(timeout_seconds),
                headers={"Accept": "application/json"},
            )
        )

    def update_token(self, token: str) -> None:
        """Update the bearer token used for subsequent API requests."""
        if not token:
            raise ValueError("SAYT API JWT must not be empty")

        self._token = token

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Search the configured API endpoint."""
        try:
            response = self._client.get(
                self._endpoint_url,
                params={
                    self._query_parameter: query,
                    "limit": limit,
                },
                headers={
                    "Authorization": f"Bearer {self._token}",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise BusinessActivityApiTimeoutError(
                "Business activity API request timed out"
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise BusinessActivityApiError("Business activity API request failed") from error

        items = payload if isinstance(payload, list) else payload.get("results")

        if not isinstance(items, list):
            raise BusinessActivityApiError("Business activity API returned an invalid response")

        suggestions: list[BusinessActivitySuggestion] = []

        for item in items[:limit]:
            if not isinstance(item, dict):
                continue

            label = item.get("en")

            if not isinstance(label, str) or not label.strip():
                continue

            code = item.get("code")

            suggestions.append(
                BusinessActivitySuggestion(
                    label=label.strip(),
                    code=code if isinstance(code, str) else None,
                )
            )

        return suggestions

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()
