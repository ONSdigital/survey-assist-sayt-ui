"""Tests for resolving survey question placeholders."""

import pytest

from survey_assist_sayt_ui.survey.models import (
    QuestionPage,
    SurveyResponses,
)
from survey_assist_sayt_ui.survey.placeholders import (
    MissingPlaceholderResponseError,
    resolve_question_text,
)


def test_resolve_question_text_replaces_saved_response(
    question_page: QuestionPage,
) -> None:
    """Test that a placeholder is replaced by its source response."""
    responses: SurveyResponses = {
        "q1": {
            "question_name": "job_title_question",
            "response_name": "job-title",
            "value": "PRIMARY schooL teaCHer",
        }
    }

    result = resolve_question_text(
        question_page,
        responses,
    )

    assert result == ("Describe what you do in that job or business as a " "primary school teacher")


def test_resolve_question_text_raises_when_response_is_missing(
    question_page: QuestionPage,
) -> None:
    """Test that an unavailable source response raises an error."""
    with pytest.raises(
        MissingPlaceholderResponseError,
        match="job_title_question",
    ):
        resolve_question_text(question_page, {})
