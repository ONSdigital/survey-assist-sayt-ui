"""Resolve placeholders in configurable survey text."""

from __future__ import annotations

from typing import cast

from survey_assist_sayt_ui.survey.models import (
    QuestionPage,
    SingleValueSurveyResponse,
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


class MissingPlaceholderValueMappingError(ValueError):
    """Raised when a placeholder response has no configured mapping."""

    def __init__(
        self,
        question_name: str,
        response_value: str,
    ) -> None:
        """Initialise the missing mapping error."""
        self.question_name = question_name
        self.response_value = response_value

        super().__init__(
            f"No placeholder value mapping exists for "
            f"{question_name!r} response {response_value!r}"
        )


def _get_single_value_responses_by_question_name(
    responses: SurveyResponses,
) -> dict[str, str]:
    """Return single-value responses indexed by question name.

    Args:
        responses: Saved survey responses.

    Returns:
        dict[str, str]: Single values keyed by question name.
    """
    response_values: dict[str, str] = {}

    for response in responses.values():
        if "value" not in response:
            continue

        single_response = cast(
            SingleValueSurveyResponse,
            response,
        )

        response_values[single_response["question_name"]] = single_response["value"]

    return response_values


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

    responses_by_question_name = _get_single_value_responses_by_question_name(
        responses,
    )

    ordered_placeholders = sorted(
        placeholders,
        key=lambda item: len(item["placeholder"]),
        reverse=True,
    )

    for placeholder_definition in ordered_placeholders:
        placeholder = placeholder_definition["placeholder"]
        source_question_name = placeholder_definition["source_question_name"]

        response_value = responses_by_question_name.get(source_question_name)

        if response_value is None:
            raise MissingPlaceholderResponseError(source_question_name)

        value_map = placeholder_definition.get("value_map")

        if value_map is not None:
            replacement = value_map.get(response_value)

            if replacement is None:
                raise MissingPlaceholderValueMappingError(
                    source_question_name,
                    response_value,
                )
        else:
            replacement = response_value

        resolved_text = resolved_text.replace(
            placeholder,
            replacement.lower(),
        )

    return resolved_text
