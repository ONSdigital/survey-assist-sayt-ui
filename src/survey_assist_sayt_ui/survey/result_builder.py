"""Build API result payloads from survey metadata."""

from datetime import datetime
import re

from survey_assist_sayt_ui.models.result import Response, SurveyAssistResult
from survey_assist_sayt_ui.survey.models import SurveyDefinition


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
