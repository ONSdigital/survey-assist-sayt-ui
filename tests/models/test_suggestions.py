"""Tests for Survey Assist suggestions models."""

from pydantic import ValidationError
import pytest

from survey_assist_sayt_ui.models.suggestions import (
    SuggestionsRequest,
    SuggestionsResponse,
    SuggestionType,
)


def test_suggestions_request_accepts_valid_sic_request() -> None:
    """Test creating a valid SIC suggestions request."""
    request = SuggestionsRequest(
        type=SuggestionType.SIC,
        query="soft",
        limit=5,
    )

    assert request.type == SuggestionType.SIC
    assert request.query == "soft"
    assert request.limit == 5


def test_suggestions_request_rejects_empty_query() -> None:
    """Test that suggestions queries cannot be empty."""
    with pytest.raises(ValidationError):
        SuggestionsRequest(
            type=SuggestionType.SIC,
            query="",
            limit=5,
        )


def test_suggestions_request_rejects_query_over_maximum_length() -> None:
    """Test that suggestions queries cannot exceed 100 characters."""
    with pytest.raises(ValidationError):
        SuggestionsRequest(
            type=SuggestionType.SIC,
            query="a" * 101,
            limit=5,
        )


def test_suggestions_request_rejects_limit_over_maximum() -> None:
    """Test that suggestion limits cannot exceed 50."""
    with pytest.raises(ValidationError):
        SuggestionsRequest(
            type=SuggestionType.SIC,
            query="software",
            limit=51,
        )


def test_suggestions_response_accepts_valid_response() -> None:
    """Test parsing a valid suggestions API response."""
    response = SuggestionsResponse.model_validate(
        {
            "suggestions": [
                {
                    "display_text": "Software development: 62012",
                }
            ]
        }
    )

    assert len(response.suggestions) == 1
    assert response.suggestions[0].display_text == "Software development: 62012"
    assert response.suggestions[0].score is None


def test_suggestions_response_accepts_optional_score() -> None:
    """Test parsing a suggestion containing a ranking score."""
    response = SuggestionsResponse.model_validate(
        {
            "suggestions": [
                {
                    "display_text": "Software development: 62012",
                    "score": 0.95,
                }
            ]
        }
    )

    assert response.suggestions[0].score == 0.95


def test_suggestions_response_rejects_missing_display_text() -> None:
    """Test that suggestions must contain display text."""
    with pytest.raises(ValidationError):
        SuggestionsResponse.model_validate(
            {
                "suggestions": [
                    {
                        "score": 0.95,
                    }
                ]
            }
        )
