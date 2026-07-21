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
from survey_assist_sayt_ui.survey.models import (
    FeedbackPage,
    FeedbackResponses,
    QuestionPage,
    SurveyDefinition,
    SurveyFeedback,
    SurveyResponses,
)
from survey_assist_sayt_ui.survey.placeholders import (
    MissingPlaceholderResponseError,
    resolve_question_text,
)
from survey_assist_sayt_ui.survey.session import (
    SURVEY_FEEDBACK_RESPONSES_KEY,
    SURVEY_RESPONSES_KEY,
)

NOT_LISTED_FIELD_SUFFIX = "-not-listed"
NOT_LISTED_VALUE = "not-listed"

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


def _get_question_template(page: QuestionPage) -> str:
    """Return the template for a configured question page.

    Args:
        page: Question page being rendered.

    Returns:
        str: Jinja template filename.
    """
    if page["answer"]["type"] == "api_autosuggest":
        return "survey_api_autosuggest.html"

    return "survey_question.html"


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


def _get_page_id_by_question_name(
    question_name: str,
) -> str:
    """Return the page identifier for a configured question.

    Args:
        question_name: Configured question name.

    Returns:
        str: Matching page identifier.

    Raises:
        RuntimeError: If the validated question cannot be found.
    """
    pages = _get_survey_definition()["survey_pages"]["pages"]

    for page in pages:
        if page["question_name"] == question_name:
            return page["page_id"]

    raise RuntimeError(f"No page exists for question {question_name!r}")


def _resolve_page_question_text(
    page: QuestionPage,
    responses: SurveyResponses,
) -> str:
    """Resolve saved response placeholders for a question.

    Args:
        page: Question page being rendered.
        responses: Responses stored in the current session.

    Returns:
        str: Resolved question text.
    """
    return resolve_question_text(page, responses)


def _get_not_listed_field_name(
    answer_name: str,
) -> str:
    """Return the checkbox field name for a Not listed option.

    Args:
        answer_name: Configured autosuggest response name.

    Returns:
        str: Generated Not listed checkbox name.
    """
    return f"{answer_name}{NOT_LISTED_FIELD_SUFFIX}"


def _get_submitted_response(
    page: QuestionPage,
) -> tuple[str, bool]:
    """Return the submitted response for a question page.

    Args:
        page: Submitted question page.

    Returns:
        tuple[str, bool]: Normalised response value and whether Not listed
            was selected.

    Raises:
        BadRequest: If an unexpected Not listed value is submitted.
    """
    answer = page["answer"]
    value = request.form.get(answer["name"], "").strip()

    if answer["type"] != "api_autosuggest":
        return value, False

    if not answer.get("not_listed", False):
        return value, False

    not_listed_field_name = _get_not_listed_field_name(answer["name"])
    not_listed_value = request.form.get(not_listed_field_name)

    if not_listed_value is None:
        return value, False

    if not_listed_value != NOT_LISTED_VALUE:
        abort(HTTPStatus.BAD_REQUEST)

    return NOT_LISTED_VALUE, True


def _get_saved_response_state(
    page: QuestionPage,
    responses: SurveyResponses,
) -> tuple[str, bool]:
    """Return the input and Not listed state for a saved response.

    Args:
        page: Question page being rendered.
        responses: Responses currently stored in the session.

    Returns:
        tuple[str, bool]: Autosuggest input value and Not listed checked state.
    """
    saved_response = responses.get(page["page_id"])

    if saved_response is None:
        return "", False

    saved_value = saved_response["value"]
    answer = page["answer"]

    if (
        answer["type"] == "api_autosuggest"
        and answer.get("not_listed", False)
        and saved_value == NOT_LISTED_VALUE
    ):
        return "", True

    return saved_value, False


def _get_survey_feedback() -> SurveyFeedback | None:
    """Return the enabled survey feedback configuration.

    Returns:
        SurveyFeedback | None: Enabled feedback configuration, or None.
    """
    survey_feedback = _get_survey_definition().get("survey_feedback")

    if survey_feedback is None:
        return None

    if not survey_feedback["enabled"]:
        return None

    return survey_feedback


def _get_feedback_page(page_id: str) -> FeedbackPage:
    """Return a feedback page by identifier.

    Args:
        page_id: Requested feedback page identifier.

    Returns:
        FeedbackPage: Matching feedback page.

    Raises:
        NotFound: If feedback is disabled or the page does not exist.
    """
    survey_feedback = _get_survey_feedback()

    if survey_feedback is None:
        abort(HTTPStatus.NOT_FOUND)

    for page in survey_feedback["pages"]:
        if page["page_id"] == page_id:
            return page

    abort(HTTPStatus.NOT_FOUND)


def _get_next_feedback_page_id(
    page_id: str,
) -> str | None:
    """Return the next feedback page identifier.

    Args:
        page_id: Current feedback page identifier.

    Returns:
        str | None: Next feedback page, or None for the final page.
    """
    survey_feedback = _get_survey_feedback()

    if survey_feedback is None:
        return None

    page_ids = [page["page_id"] for page in survey_feedback["pages"]]
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
    responses = cast(
        SurveyResponses,
        session.get(SURVEY_RESPONSES_KEY, {}),
    )

    try:
        question_text = _resolve_page_question_text(
            page,
            responses,
        )
        logger.info(
            "Rendering question page_id=%s question_text=%s",
            page_id,
            question_text,
        )
    except MissingPlaceholderResponseError as exc:
        logger.warning(
            "Placeholder response missing page_id=%s source_question_name=%s",
            page_id,
            exc.question_name,
        )
        return redirect(
            url_for(
                "survey.question",
                page_id=_get_page_id_by_question_name(exc.question_name),
            )
        )

    saved_value, not_listed_selected = _get_saved_response_state(
        page,
        responses,
    )

    template_name = _get_question_template(page)

    return render_template(
        template_name,
        page=page,
        question_text=question_text,
        saved_value=saved_value,
        not_listed_selected=not_listed_selected,
        form_action=url_for("survey.save_response", page_id=page_id),
        error_message=None,
    )


@survey_blueprint.post("/questions/<page_id>")
@login_required
def save_response(page_id: str) -> ResponseReturnValue:
    """Save a survey response and continue to the next page.

    Args:
        page_id: Submitted survey page identifier.

    Returns:
        ResponseReturnValue: Redirect to the next configured page or a
            validation error response.
    """
    page = _get_question_page(page_id)
    answer = page["answer"]
    responses = cast(
        SurveyResponses,
        session.get(SURVEY_RESPONSES_KEY, {}),
    )

    try:
        question_text = _resolve_page_question_text(
            page,
            responses,
        )
    except MissingPlaceholderResponseError as exc:
        logger.warning(
            "Placeholder response missing page_id=%s source_question_name=%s",
            page_id,
            exc.question_name,
        )
        return redirect(
            url_for(
                "survey.question",
                page_id=_get_page_id_by_question_name(
                    exc.question_name,
                ),
            )
        )

    value, not_listed_selected = _get_submitted_response(page)

    if answer["required"] and not value:
        logger.warning(
            "question text: %s page_id=%s missing required response",
            question_text,
            page_id,
        )
        return (
            render_template(
                _get_question_template(page),
                page=page,
                question_text=question_text,
                saved_value=value,
                not_listed_selected=not_listed_selected,
                form_action=url_for("survey.save_response", page_id=page_id),
                error_message="Enter an answer",
            ),
            HTTPStatus.BAD_REQUEST,
        )

    if answer["type"] == "radio":
        allowed_values = {option["value"] for option in answer["options"]}

        if value not in allowed_values:
            abort(HTTPStatus.BAD_REQUEST)

    updated_responses = dict(responses)
    updated_responses[page_id] = {
        "question_name": page["question_name"],
        "response_name": answer["name"],
        "value": value,
    }
    session[SURVEY_RESPONSES_KEY] = updated_responses

    next_page_id = _get_next_page_id(page_id)

    # Is this the last question?
    # Either route to feedback section or show the survey completion page.
    if next_page_id is None:
        survey_feedback = _get_survey_feedback()

        if survey_feedback is not None:
            return redirect(
                url_for(
                    "survey.feedback_question",
                    page_id=survey_feedback["start_page_id"],
                )
            )

        return redirect(url_for("survey.complete"))

    return redirect(
        url_for(
            "survey.question",
            page_id=next_page_id,
        )
    )


@survey_blueprint.get("/feedback/<page_id>")
@login_required
def feedback_question(
    page_id: str,
) -> ResponseReturnValue:
    """Render a configured survey feedback question.

    Args:
        page_id: Requested feedback page identifier.

    Returns:
        ResponseReturnValue: Rendered feedback question page.
    """
    page = _get_feedback_page(page_id)
    responses = cast(
        FeedbackResponses,
        session.get(
            SURVEY_FEEDBACK_RESPONSES_KEY,
            {},
        ),
    )
    saved_response = responses.get(page_id)
    saved_value = saved_response["value"] if saved_response is not None else ""

    return render_template(
        "survey_question.html",
        page=page,
        question_text=page["question"]["text"],
        saved_value=saved_value,
        form_action=url_for(
            "survey.save_feedback_response",
            page_id=page_id,
        ),
        error_message=None,
    )


@survey_blueprint.post("/feedback/<page_id>")
@login_required
def save_feedback_response(
    page_id: str,
) -> ResponseReturnValue:
    """Save a feedback response and continue.

    Optional blank answers are not retained in the feedback session.

    Args:
        page_id: Submitted feedback page identifier.

    Returns:
        ResponseReturnValue: Redirect or validation error response.
    """
    page = _get_feedback_page(page_id)
    answer = page["answer"]
    value = request.form.get(
        answer["name"],
        "",
    ).strip()

    if answer["required"] and not value:
        return (
            render_template(
                "survey_question.html",
                page=page,
                question_text=page["question"]["text"],
                saved_value=value,
                form_action=url_for(
                    "survey.save_feedback_response",
                    page_id=page_id,
                ),
                error_message="Select an answer",
            ),
            HTTPStatus.BAD_REQUEST,
        )

    if answer["type"] == "radio" and value:
        allowed_values = {option["value"] for option in answer["options"]}

        if value not in allowed_values:
            abort(HTTPStatus.BAD_REQUEST)

    responses = cast(
        FeedbackResponses,
        session.get(
            SURVEY_FEEDBACK_RESPONSES_KEY,
            {},
        ),
    )
    updated_responses = dict(responses)

    if value:
        updated_responses[page_id] = {
            "question_name": page["question_name"],
            "response_name": answer["name"],
            "value": value,
        }
    else:
        updated_responses.pop(page_id, None)

    session[SURVEY_FEEDBACK_RESPONSES_KEY] = updated_responses

    next_page_id = _get_next_feedback_page_id(page_id)

    if next_page_id is None:
        return redirect(url_for("survey.complete"))

    return redirect(
        url_for(
            "survey.feedback_question",
            page_id=next_page_id,
        )
    )


@survey_blueprint.get("/complete")
@login_required
def complete() -> ResponseReturnValue:
    """Render the temporary survey completion page.

    Returns:
        ResponseReturnValue: Completion page response.
    """

    survey_definition = _get_survey_definition()
    survey_responses = session.get(SURVEY_RESPONSES_KEY, {})
    feedback_responses = session.get(
        SURVEY_FEEDBACK_RESPONSES_KEY,
        {},
    )

    logger.info(
        "Survey completed wave_id=%s survey_responses=%s feedback_responses=%s",
        survey_definition["wave_id"],
        survey_responses,
        feedback_responses,
    )

    return render_template(
        "survey_complete.html",
        responses=survey_responses,
        feedback_responses=feedback_responses,
    )
