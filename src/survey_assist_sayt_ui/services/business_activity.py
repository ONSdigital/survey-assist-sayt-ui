"""Client for retrieving business activity suggestions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


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

    def __init__(  # pylint: disable=too-many-arguments
        self,
        endpoint_url: str,
        token: str,
        *,
        query_parameter: str = "q",
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
        token_refresher: Callable[[], str] | None = None,
    ) -> None:
        if not endpoint_url:
            raise ValueError("SAYT_API_URL must be configured")

        if not token:
            raise ValueError("SAYT API JWT must be configured")

        self._endpoint_url = endpoint_url
        self._query_parameter = query_parameter
        self._token = token
        self._token_refresher = token_refresher
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

    def _get_suggestions_response(self, query: str) -> httpx.Response:
        """Get the raw HTTP response from the business activity API."""
        return self._client.get(
            self._endpoint_url,
            params={
                self._query_parameter: query,
                "similarity": "true",
            },
            headers={
                "Authorization": f"Bearer {self._token}",
            },
        )

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Search the configured API endpoint."""
        try:
            response = self._get_suggestions_response(query)

            # If the API returns a 401 Unauthorized, attempt to refresh the token and retry once.
            if (
                response.status_code == HTTPStatus.UNAUTHORIZED
                and self._token_refresher is not None
            ):
                logger.info("SAYT API returned 401; refreshing JWT and retrying once")
                self.update_token(self._token_refresher())
                response = self._get_suggestions_response(query)

            logger.info(
                "SAYT API response status=%s content_type=%s url=%s",
                response.status_code,
                response.headers.get("content-type"),
                response.request.url,
            )

            response.raise_for_status()
            payload = response.json()

            logger.info(
                "SAYT API payload type=%s keys=%s",
                type(payload).__name__,
                list(payload) if isinstance(payload, dict) else None,
            )

            logger.info(
                "SAYT API response body=%s",
                response.text[:1000],
            )

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
