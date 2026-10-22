"""Build API feedback payloads from the survey definition and session."""

import logging
import re

from survey_assist_sayt_ui.models.feedback import FeedbackQuestion, FeedbackResult
from survey_assist_sayt_ui.survey.models import (
    FeedbackResponses,
    SurveyDefinition,
)

logger = logging.getLogger(__name__)


def build_feedback_result(
    survey_definition: SurveyDefinition,
    feedback_responses: FeedbackResponses,
    *,
    case_id: str,
    person_id: str,
) -> FeedbackResult:
    """Build a feedback payload from answers held in the session.

    Questions follow the survey definition order. When any question was
    answered, an optional question with no answer is included as an empty
    string. A required question with no saved answer is left out, and a
    warning is written. Radio questions send their option labels. Other
    questions send no options.
    """
    survey_id = re.sub(
        r"\s+",
        "_",
        survey_definition["survey_title"].strip().lower(),
    )
    feedback_pages = survey_definition.get("survey_feedback", {}).get("pages", [])
    questions: list[FeedbackQuestion] = []

    for page in feedback_pages:
        saved = feedback_responses.get(page["page_id"])
        answer = page["answer"]

        if saved is not None and saved["value"]:
            response = saved["value"]
            response_name = saved["response_name"]
        elif answer["required"]:
            logger.warning(
                "Required feedback question has no saved answer page_id=%s",
                page["page_id"],
            )
            continue
        else:
            response = ""
            response_name = answer["name"]

        response_options = (
            [option["label"] for option in answer["options"]] if answer["type"] == "radio" else None
        )
        questions.append(
            FeedbackQuestion(
                response=response,
                response_name=response_name,
                response_options=response_options,
            )
        )

    if not any(question.response for question in questions):
        questions = []

    return FeedbackResult(
        survey_id=survey_id,
        wave_id=survey_definition["wave_id"],
        case_id=case_id,
        person_id=person_id,
        questions=questions,
    )
