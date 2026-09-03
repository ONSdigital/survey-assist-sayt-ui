"""Client for retrieving business activity suggestions."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from pydantic import ValidationError

from survey_assist_sayt_ui.models.suggestions import (
    SuggestionsRequest,
    SuggestionsResponse,
    SuggestionType,
)
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

    def to_dict(self) -> dict[str, str]:
        """Convert the suggestion to the ONS language-keyed format."""
        return {"en": self.label}


class BusinessActivitySearchClient(Protocol):  # pylint: disable=too-few-public-methods
    """Interface for business activity search implementations."""

    def search(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[BusinessActivitySuggestion]:
        """Search for matching business activities."""


SUGGESTIONS_ENDPOINT = "suggestions"
MOCK_BUSINESS_ACTIVITY_API = False


class HttpBusinessActivitySearchClient:  # pylint: disable=too-few-public-methods
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
            request = SuggestionsRequest(
                type=SuggestionType.SIC,
                query=query,
                limit=limit,
            )

            response = self._api_client.post(
                SUGGESTIONS_ENDPOINT,
                body=request.model_dump(mode="json", exclude_none=True),
            )
            result = SuggestionsResponse.model_validate(response.json())

        except SurveyAssistApiTimeoutError as error:
            raise BusinessActivityApiTimeoutError(
                "Business activity API request timed out"
            ) from error
        except (
            SurveyAssistApiError,
            ValidationError,
            ValueError,
        ) as error:
            raise BusinessActivityApiError("Business activity API request failed") from error

        return [
            BusinessActivitySuggestion(label=suggestion.display_text)
            for suggestion in result.suggestions
        ]
