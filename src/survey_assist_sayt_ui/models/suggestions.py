"""Request and response models for Survey Assist suggestions."""

from enum import Enum

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Supported suggestion sources."""

    SIC = "sic"


class SuggestionsRequest(BaseModel):
    """Request payload for the Survey Assist suggestions endpoint."""

    type: SuggestionType
    query: str = Field(min_length=1, max_length=100)
    limit: int | None = Field(default=None, gt=0, le=50)


class Suggestion(BaseModel):
    """A suggestion returned by the Survey Assist API."""

    display_text: str
    score: float | None = None


class SuggestionsResponse(BaseModel):
    """Response returned by the Survey Assist suggestions endpoint."""

    suggestions: list[Suggestion]
