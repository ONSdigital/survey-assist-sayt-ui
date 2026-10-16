"""Build API result payloads from survey metadata."""

from datetime import datetime
import re
from typing import cast

from survey_assist_sayt_ui.models.result import (
    InputField,
    Response,
    SuggestionInteraction,
    SuggestionListItem,
    SuggestionResponse,
    SurveyAssistResult,
)
from survey_assist_sayt_ui.survey.models import (
    MultiTextSurveyResponse,
    SingleValueSurveyResponse,
    SurveyDefinition,
    SurveyResponses,
)


def build_suggestion_inputs(
    survey_definition: SurveyDefinition,
    responses: SurveyResponses,
) -> list[InputField]:
    """Build inputs in configured survey question order."""
    inputs: list[InputField] = []

    for page in survey_definition["survey_pages"]["pages"]:
        if page["page_type"] != "question":
            continue

        saved = responses.get(page["page_id"])
        if saved is None:
            continue

        if "values" in saved:
            multi_response = cast(MultiTextSurveyResponse, saved)

            for name, value in multi_response["values"].items():
                inputs.append(
                    InputField(
                        field=name,
                        value=value,
                    )
                )
        else:
            inputs.append(
                InputField(
                    field=saved["response_name"],
                    value=saved["value"],
                )
            )

    return inputs


def get_not_listed_description(
    survey_definition: SurveyDefinition,
    responses: SurveyResponses,
) -> str:
    """Return the saved SAYT Not Listed self-description, if present."""

    for page in survey_definition["survey_pages"]["pages"]:
        if page["page_type"] != "question":
            continue

        answer = page["answer"]

        if answer["type"] != "api_autosuggest":
            continue

        saved = responses.get(page["page_id"])

        if saved is None or "value" not in saved:
            continue

        single_response = cast(SingleValueSurveyResponse, saved)

        expected_field_name = f"{page['page_id']}-self-describe"

        if single_response["response_name"] == expected_field_name:
            return single_response["value"]

    return ""


def get_selected_suggestion(
    survey_definition: SurveyDefinition,
    responses: SurveyResponses,
) -> str:
    """Return the selected SAYT description, if one was chosen."""

    for page in survey_definition["survey_pages"]["pages"]:
        if page["page_type"] != "question":
            continue

        answer = page["answer"]

        if answer["type"] != "api_autosuggest":
            continue

        saved = responses.get(page["page_id"])

        if saved is None or "value" not in saved:
            continue

        single_response = cast(SingleValueSurveyResponse, saved)

        # Not Listed uses the generated self-description field name.
        expected_field_name = f"{page['page_id']}-self-describe"

        if single_response["response_name"] == expected_field_name:
            return ""

        return single_response["value"]

    return ""


def get_last_suggestions(
    survey_definition: SurveyDefinition,
    responses: SurveyResponses,
) -> list[SuggestionListItem]:
    """Return the last displayed suggestions from the answered SAYT question."""

    for page in survey_definition["survey_pages"]["pages"]:
        if page["page_type"] != "question":
            continue

        if page["answer"]["type"] != "api_autosuggest":
            continue

        saved = responses.get(page["page_id"])

        if saved is None or "value" not in saved:
            continue

        single_response = cast(SingleValueSurveyResponse, saved)

        return [
            SuggestionListItem(
                code="99999",  # Placeholder until code is added to api
                description=description,
            )
            for description in single_response.get("suggestions", [])
        ]

    return []


def build_suggestion_survey_result(  # pylint: disable=too-many-arguments
    survey_definition: SurveyDefinition,
    *,
    case_id: str,
    user: str,
    person_id: str,
    survey_time_start: datetime,
    response_time_start: datetime,
    time_end: datetime,
    responses: SurveyResponses,
    suggestion_time_start: datetime,
    suggestion_time_end: datetime,
) -> SurveyAssistResult:
    """Build a survey result with a placeholder SAYT interaction."""

    result = build_empty_survey_result(
        survey_definition,
        case_id=case_id,
        user=user,
        person_id=person_id,
        survey_time_start=survey_time_start,
        response_time_start=response_time_start,
        time_end=time_end,
    )

    selected_description = get_selected_suggestion(
        survey_definition,
        responses,
    )

    interaction = SuggestionInteraction(
        time_start=suggestion_time_start,
        time_end=suggestion_time_end,
        input=build_suggestion_inputs(
            survey_definition,
            responses,
        ),
        queries_sent=0,
        queries=[],
        response=SuggestionResponse(
            listed=bool(selected_description),
            code="99999" if selected_description else "",
            description=selected_description,
            suggestions=get_last_suggestions(
                survey_definition,
                responses,
            ),
            not_listed_description=get_not_listed_description(
                survey_definition,
                responses,
            ),
        ),
    )

    result.responses[0].survey_assist_interactions.append(interaction)

    return result


def build_empty_survey_result(  # pylint: disable=too-many-arguments
    survey_definition: SurveyDefinition,
    *,
    case_id: str,
    user: str,
    person_id: str,
    survey_time_start: datetime,
    response_time_start: datetime,
    time_end: datetime,
) -> SurveyAssistResult:
    """Build a result payload with no recorded Survey Assist interactions."""
    survey_id = re.sub(
        r"\s+",
        "_",
        survey_definition["survey_title"].strip().lower(),
    )

    return SurveyAssistResult(
        survey_id=survey_id,
        wave_id=survey_definition["wave_id"],
        case_id=case_id,
        user=user,
        time_start=survey_time_start,
        time_end=time_end,
        responses=[
            Response(
                person_id=person_id,
                time_start=response_time_start,
                time_end=time_end,
                survey_assist_interactions=[],
            ),
        ],
    )
