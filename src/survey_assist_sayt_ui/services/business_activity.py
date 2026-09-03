"""Client for retrieving business activity suggestions."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from survey_assist_sayt_ui.services.survey_assist_api import (
    SurveyAssistApiClient,
    SurveyAssistApiError,
    SurveyAssistApiTimeoutError,
)


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


SIC_LOOKUP_ENDPOINT = "sic-lookup"
SUGGESTIONS_ENDPOINT = "suggestions"
MOCK_BUSINESS_ACTIVITY_API = True


class HttpBusinessActivitySearchClient:
    """Survey Assist API implementation of business activity search."""

    def __init__(
        self,
        api_client: SurveyAssistApiClient,
    ) -> None:
        self._api_client = api_client

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Search for matching business activities."""

        if MOCK_BUSINESS_ACTIVITY_API:
            time.sleep(0.5)  # Simulate network latency

            # Temporary mock for SA858 wireframe sharing.
            return [
                BusinessActivitySuggestion(label=f"Example search response {index}")
                for index in range(1, 9)
            ][:limit]

        try:
            response = self._api_client.get(
                SIC_LOOKUP_ENDPOINT,
                params={
                    "description": query,
                    "similarity": "true",
                },
            )
            payload = response.json()

        except SurveyAssistApiTimeoutError as error:
            raise BusinessActivityApiTimeoutError(
                "Business activity API request timed out"
            ) from error
        except (SurveyAssistApiError, ValueError) as error:
            raise BusinessActivityApiError("Business activity API request failed") from error

        items: object

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("results")
        else:
            items = None

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
