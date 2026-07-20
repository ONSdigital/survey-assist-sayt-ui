"""Routes for configurable survey pages."""

from __future__ import annotations

from http import HTTPStatus
import logging
from typing import cast

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.typing import ResponseReturnValue

from survey_assist_sayt_ui.auth.decorators import login_required
from survey_assist_sayt_ui.survey.models import QuestionPage, SurveyDefinition
from survey_assist_sayt_ui.survey.session import SURVEY_RESPONSES_KEY

logger = logging.getLogger(__name__)

survey_blueprint = Blueprint(
    "survey",
    __name__,
    url_prefix="/wireframe",
)


def _get_survey_definition() -> SurveyDefinition:
    """Return the configured survey definition.

    Returns:
        SurveyDefinition: Survey loaded during application startup.
    """
    return cast(
        SurveyDefinition,
        current_app.extensions["survey_definition"],
    )


def _get_question_page(page_id: str) -> QuestionPage:
    """Return a question page by identifier.

    Args:
        page_id: Requested survey page identifier.

    Returns:
        QuestionPage: Matching question page.

    Raises:
        NotFound: If the page does not exist.
    """
    pages = _get_survey_definition()["survey_pages"]["pages"]

    for page in pages:
        if page["page_id"] == page_id:
            return page

    abort(HTTPStatus.NOT_FOUND)


def _get_next_page_id(page_id: str) -> str | None:
    """Return the next configured page identifier.

    Args:
        page_id: Current survey page identifier.

    Returns:
        str | None: Next page identifier, or None for the final page.
    """
    pages = _get_survey_definition()["survey_pages"]["pages"]
    page_ids = [page["page_id"] for page in pages]
    current_index = page_ids.index(page_id)

    if current_index + 1 >= len(page_ids):
        return None

    return page_ids[current_index + 1]


@survey_blueprint.get("/questions/<page_id>")
@login_required
def question(page_id: str) -> ResponseReturnValue:
    """Render a configured survey question.

    Args:
        page_id: Requested survey page identifier.

    Returns:
        ResponseReturnValue: Rendered ONS question page.
    """
    page = _get_question_page(page_id)
    responses = session.get(SURVEY_RESPONSES_KEY, {})

    return render_template(
        "survey_question.html",
        page=page,
        saved_value=responses.get(page_id, {}).get("value", ""),
        error_message=None,
    )


@survey_blueprint.post("/questions/<page_id>")
@login_required
def save_response(page_id: str) -> ResponseReturnValue:
    """Save a survey response and continue to the next page.

    Args:
        page_id: Submitted survey page identifier.

    Returns:
        ResponseReturnValue: Redirect to the next configured page.
    """
    page = _get_question_page(page_id)
    answer = page["answer"]
    value = request.form.get(answer["name"], "").strip()

    if answer["required"] and not value:
        return (
            render_template(
                "survey_question.html",
                page=page,
                saved_value=value,
                error_message="Enter an answer",
            ),
            HTTPStatus.BAD_REQUEST,
        )

    if answer["type"] == "radio":
        allowed_values = {option["value"] for option in answer["options"]}
        if value not in allowed_values:
            abort(HTTPStatus.BAD_REQUEST)

    responses = dict(session.get(SURVEY_RESPONSES_KEY, {}))
    responses[page_id] = {
        "question_name": page["question_name"],
        "response_name": answer["name"],
        "value": value,
    }
    session[SURVEY_RESPONSES_KEY] = responses

    next_page_id = _get_next_page_id(page_id)

    if next_page_id is None:
        return redirect(url_for("survey.complete"))

    return redirect(url_for("survey.question", page_id=next_page_id))


@survey_blueprint.get("/complete")
@login_required
def complete() -> ResponseReturnValue:
    """Render the temporary survey completion page.

    Returns:
        ResponseReturnValue: Completion page response.
    """

    survey_definition = _get_survey_definition()
    responses = session.get(SURVEY_RESPONSES_KEY, {})

    logger.info(
        "Survey completed wave_id=%s responses=%s",
        survey_definition["wave_id"],
        responses,
    )

    return render_template(
        "survey_complete.html",
        responses=session.get(SURVEY_RESPONSES_KEY, {}),
    )
