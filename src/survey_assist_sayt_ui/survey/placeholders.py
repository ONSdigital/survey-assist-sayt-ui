"""Resolve placeholders in configurable survey text."""

from __future__ import annotations

from survey_assist_sayt_ui.survey.models import (
    QuestionPage,
    SurveyResponses,
)


class MissingPlaceholderResponseError(ValueError):
    """Raised when placeholder source response data is unavailable."""

    def __init__(self, question_name: str) -> None:
        """Initialise the missing response error.

        Args:
            question_name: Question name required by the placeholder.
        """
        self.question_name = question_name
        super().__init__(f"No response exists for question {question_name!r}")


def resolve_question_text(
    page: QuestionPage,
    responses: SurveyResponses,
) -> str:
    """Replace question text placeholders with saved responses.

    Args:
        page: Question page being rendered.
        responses: Responses currently stored in the survey session.

    Returns:
        str: Question text containing resolved response values.

    Raises:
        MissingPlaceholderResponseError: If a referenced response has not
            been saved.
    """
    question = page["question"]
    resolved_text = question["text"]
    placeholders = question.get("placeholders", [])

    responses_by_question_name = {
        response["question_name"]: response["value"] for response in responses.values()
    }

    ordered_placeholders = sorted(
        placeholders,
        key=lambda item: len(item["placeholder"]),
        reverse=True,
    )

    for placeholder_definition in ordered_placeholders:
        placeholder = placeholder_definition["placeholder"]
        source_question_name = placeholder_definition["source_question_name"]

        replacement = responses_by_question_name.get(source_question_name)

        if replacement is None:
            raise MissingPlaceholderResponseError(source_question_name)

        resolved_text = resolved_text.replace(
            placeholder,
            replacement.lower(),
        )

    return resolved_text
