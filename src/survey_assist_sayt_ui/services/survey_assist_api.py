"""HTTP client for the Survey Assist API."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]
QueryParameters = dict[str, str | int | float | bool]


class SurveyAssistApiError(RuntimeError):
    """Raised when a Survey Assist API request fails."""


class SurveyAssistApiTimeoutError(SurveyAssistApiError):
    """Raised when a Survey Assist API request times out."""


class SurveyAssistApiClient:
    """Authenticated HTTP client for the Survey Assist API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
        token_refresher: Callable[[], str] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("SURVEY_ASSIST_API_BASE_URL must be configured")

        if not token:
            raise ValueError("Survey Assist API JWT must be configured")

        self._base_url = base_url.rstrip("/")
        self._token = token
        self._token_refresher = token_refresher
        self._client = (
            client
            if client is not None
            else httpx.Client(
                timeout=httpx.Timeout(timeout_seconds),
            )
        )

    def update_token(self, token: str) -> None:
        """Update the bearer token used for subsequent API requests."""
        if not token:
            raise ValueError("Survey Assist API JWT must not be empty")

        self._token = token

    def get(
        self,
        endpoint: str,
        *,
        params: QueryParameters | None = None,
    ) -> httpx.Response:
        """Send an authenticated GET request to the Survey Assist API."""
        return self._request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        *,
        body: JsonObject,
    ) -> httpx.Response:
        """Send an authenticated POST request to the Survey Assist API."""
        return self._request("POST", endpoint, body=body)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: QueryParameters | None = None,
        body: JsonObject | None = None,
    ) -> httpx.Response:
        """
        Send a request, retrying after request and gateway timeout and
        refreshing the bearer token once after a 401 response.
        """
        try:
            try:
                response = self._send_request(
                    method,
                    endpoint,
                    params=params,
                    body=body,
                )
            except httpx.TimeoutException:
                logger.info("Survey Assist API request timed out; retrying once")
                response = self._send_request(
                    method,
                    endpoint,
                    params=params,
                    body=body,
                )

            if response.status_code == HTTPStatus.GATEWAY_TIMEOUT:
                logger.info("SAYT API returned 504; retrying once")
                response = self._send_request(
                    method,
                    endpoint,
                    params=params,
                    body=body,
                )

            if (
                response.status_code == HTTPStatus.UNAUTHORIZED
                and self._token_refresher is not None
            ):
                logger.info("Survey Assist API returned 401; refreshing JWT and retrying once")
                self.update_token(self._token_refresher())
                response = self._send_request(
                    method,
                    endpoint,
                    params=params,
                    body=body,
                )

            logger.info(
                "Survey Assist API response status=%s method=%s endpoint=%s",
                response.status_code,
                method,
                endpoint,
            )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as error:
            raise SurveyAssistApiTimeoutError("Survey Assist API request timed out") from error
        except httpx.HTTPError as error:
            raise SurveyAssistApiError("Survey Assist API request failed") from error

    def _send_request(
        self,
        method: str,
        endpoint: str,
        *,
        params: QueryParameters | None,
        body: JsonObject | None,
    ) -> httpx.Response:
        """Send one HTTP request using the current bearer token."""
        return self._client.request(
            method,
            self._build_url(endpoint),
            params=params,
            json=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
        )

    def _build_url(self, endpoint: str) -> str:
        """Build an absolute URL from the configured API base and endpoint path."""
        if not endpoint.strip():
            raise ValueError("Survey Assist API endpoint must not be empty")

        return f"{self._base_url}/{endpoint.lstrip('/')}"

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()
