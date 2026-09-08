"""Tests for resolving survey question placeholders."""
# pylint: disable=duplicate-code

from typing import cast

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


@pytest.mark.parametrize(
    ("response_value", "expected_replacement"),
    [
        ("employee", "business or organisation"),
        ("self-employed", "business or freelance work"),
    ],
)
def test_resolve_question_text_uses_configured_value_map(
    response_value: str,
    expected_replacement: str,
) -> None:
    """Test that the placeholder is replaced according to the value map."""
    page = cast(
        QuestionPage,
        {
            "page_id": "q2",
            "page_type": "question",
            "page_title": "Business Activity",
            "question_name": "business_activity_question",
            "question": {
                "text": "What is the main activity of the PLACEHOLDER_TEXT?",
                "placeholders": [
                    {
                        "placeholder": "PLACEHOLDER_TEXT",
                        "source_question_name": "emp_status_question",
                        "value_map": {
                            "employee": "business or organisation",
                            "self-employed": "business or freelance work",
                        },
                    }
                ],
            },
            "answer": {
                "type": "text",
                "name": "business-activity",
                "required": True,
            },
            "submit_button": {
                "text": "Save and continue",
            },
        },
    )

    responses: SurveyResponses = {
        "q1": {
            "question_name": "emp_status_question",
            "response_name": "emp-status",
            "value": response_value,
        }
    }

    assert resolve_question_text(page, responses) == (
        f"What is the main activity of the {expected_replacement}?"
    )


def test_resolve_question_text_ignores_unrelated_multi_text_response(
    question_page: QuestionPage,
) -> None:
    """Test that multi-text responses do not break placeholders."""
    responses: SurveyResponses = {
        "q-about-you": {
            "question_name": "about_you_question",
            "values": {
                "first-name": "Ada",
                "middle-names": "",
                "surname": "Lovelace",
            },
        },
        "q1": {
            "question_name": "job_title_question",
            "response_name": "job-title",
            "value": "Teacher",
        },
    }

    result = resolve_question_text(
        question_page,
        responses,
    )

    assert result == ("Describe what you do in that job or business as a teacher")
