"""Tests for configurable survey routes."""

# pylint: disable=too-many-lines, duplicate-code
from datetime import UTC, datetime
from http import HTTPStatus
from typing import cast

from flask import Flask
from flask.testing import FlaskClient

from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_RESULT_USER_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.models.result import (
    ResultResponse,
    SurveyAssistResult,
)
from survey_assist_sayt_ui.routes.survey import SURVEY_RESPONSES_KEY
from survey_assist_sayt_ui.survey.models import (
    ApiAutosuggestAnswer,
    GuidancePage,
    QuestionPage,
    SurveyDefinition,
    SurveyFeedback,
)
from survey_assist_sayt_ui.survey.session import (
    SURVEY_FEEDBACK_RESPONSES_KEY,
    SURVEY_RESPONSE_START_TIME_KEY,
)


class StubSurveyResultSubmissionClient:  # pylint: disable=too-few-public-methods
    """Capture submitted survey results for tests."""

    def __init__(self) -> None:
        self.submitted_results: list[SurveyAssistResult] = []

    def submit(
        self,
        result: SurveyAssistResult,
    ) -> ResultResponse:
        """Capture and acknowledge a submitted result."""
        self.submitted_results.append(result)

        return ResultResponse(
            message="Result stored successfully",
            result_id="result-123",
        )


def _set_result_session(
    client: FlaskClient,
) -> None:
    """Configure result metadata in the test session."""
    with client.session_transaction() as flask_session:
        flask_session[SESSION_RESULT_USER_KEY] = "11-01"
        flask_session[SESSION_LOGIN_TIME_KEY] = "2026-09-25T09:00:00+00:00"
        flask_session[SURVEY_RESPONSE_START_TIME_KEY] = "2026-09-25T09:05:00+00:00"


def _authenticate(client: FlaskClient) -> None:
    """Authenticate the Flask test client.

    Args:
        client: Flask test client to authenticate.
    """
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"


def _insert_guidance_page(
    app: Flask,
    page: GuidancePage,
    index: int,
) -> None:
    """Insert guidance into the configured survey.

    Args:
        app: Configured Flask application.
        page: Guidance page to insert.
        index: Position in the ordered page list.
    """
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_pages"]["pages"].insert(
        index,
        page,
    )


def test_first_question_renders(client: FlaskClient) -> None:
    """Test that the first configured question renders."""
    _authenticate(client)

    response = client.get("/survey/questions/q0")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Select your age range from the options below" in response_text
    assert "16-24" in response_text
    assert "25-34" in response_text


def test_invalid_question_page_returns_not_found(
    client: FlaskClient,
) -> None:
    """Test that an unknown question page returns not found."""
    _authenticate(client)

    response = client.get("/survey/questions/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_required_response_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Test that an empty required response is rejected."""
    _authenticate(client)

    response = client.post(
        "/survey/questions/q0",
        data={},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_radio_value_outside_configured_options_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Test that an unconfigured radio value is rejected."""
    _authenticate(client)

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "not-configured"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_response_is_saved_in_session(
    client: FlaskClient,
) -> None:
    """Test that a valid response is stored in the session."""
    _authenticate(client)

    client.post(
        "/survey/questions/q0",
        data={"age-range": "25-34"},
    )

    with client.session_transaction() as flask_session:
        responses = cast(
            dict[str, dict[str, str]],
            flask_session[SURVEY_RESPONSES_KEY],
        )

    assert responses["q0"] == {
        "question_name": "age_range_question",
        "response_name": "age-range",
        "value": "25-34",
    }


def test_first_question_redirects_to_second_question(
    client: FlaskClient,
) -> None:
    """Test that the first question redirects to the next question."""
    _authenticate(client)

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "16-24"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q1")


def test_final_question_redirects_to_completion(
    client: FlaskClient,
) -> None:
    """Test that the final question redirects to completion."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Primary school teacher",
            }
        }

    response = client.post(
        "/survey/questions/q2",
        data={"job-description": ("I plan lessons and teach primary school pupils.")},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/complete")


def test_saved_response_is_repopulated_when_revisiting_page(
    client: FlaskClient,
) -> None:
    """Test that a previously saved response is rendered again."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Primary school teacher",
            }
        }

    response = client.get("/survey/questions/q1")

    assert response.status_code == HTTPStatus.OK
    assert "Primary school teacher" in response.get_data(as_text=True)


def test_question_renders_saved_response_in_placeholder(
    client: FlaskClient,
) -> None:
    """Test that saved answers appear in later question text."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Primary school teacher",
            }
        }

    response = client.get("/survey/questions/q2")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "as a primary school teacher" in response_text
    assert "PLACEHOLDER_TEXT" not in response_text


def test_question_redirects_when_placeholder_response_is_missing(
    client: FlaskClient,
) -> None:
    """Test that missing source answers redirect to their question."""
    _authenticate(client)

    response = client.get("/survey/questions/q2")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q1")


def _enable_autosuggest_self_describe(
    page: QuestionPage,
) -> None:
    """Enable self-description for an autosuggest question."""
    answer = cast(
        ApiAutosuggestAnswer,
        page["answer"],
    )
    answer["not_listed"] = True
    answer["self_describe"] = {
        "label": "Describe your organisation activity",
        "required_error": "Enter your organisation activity",
    }


def _insert_autosuggest_page(
    app: Flask,
    page: QuestionPage,
) -> None:
    """Insert an autosuggest page into the test survey.

    Args:
        app: Configured Flask application.
        page: Autosuggest page to insert.
    """
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_pages"]["pages"].insert(1, page)


def test_api_autosuggest_question_renders(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that an API autosuggest question renders."""
    _authenticate(client)
    _insert_autosuggest_page(app, api_autosuggest_page)

    response = client.get("/survey/questions/q-api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "What is the main activity" in response_text, response_text
    assert "/api/business-activity-suggestions" in response_text
    assert "remote-autosuggest.bundle.js" in response_text


def test_api_autosuggest_response_is_saved_and_progresses(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that an autosuggest response is saved before continuing."""
    _authenticate(client)
    _insert_autosuggest_page(app, api_autosuggest_page)

    response = client.post(
        "/survey/questions/q-api-autosuggest",
        data={"business-activity": ("Retail sale of clothing in specialised stores")},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q1")

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

    assert responses["q-api-autosuggest"] == {
        "question_name": "business_activity_question",
        "response_name": "business-activity",
        "value": ("Retail sale of clothing in specialised stores"),
    }


def test_api_autosuggest_renders_not_listed_when_enabled(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that Not listed is rendered when configured."""
    _authenticate(client)

    answer = cast(
        ApiAutosuggestAnswer,
        api_autosuggest_page["answer"],
    )
    answer["not_listed"] = True
    _insert_autosuggest_page(app, api_autosuggest_page)

    response = client.get("/survey/questions/q-api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Not listed" in response_text
    assert 'name="business-activity-not-listed"' in response_text


def test_api_autosuggest_omits_not_listed_when_disabled(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that Not listed is omitted when not configured."""
    _authenticate(client)
    _insert_autosuggest_page(app, api_autosuggest_page)

    response = client.get("/survey/questions/q-api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Not listed" not in response_text
    assert "business-activity-not-listed" not in response_text


def test_api_autosuggest_saves_self_described_response(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that a Not listed description is stored."""
    _authenticate(client)
    _enable_autosuggest_self_describe(api_autosuggest_page)
    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    response = client.post(
        "/survey/questions/q-api-autosuggest",
        data={
            "business-activity": "",
            "business-activity-not-listed": "not-listed",
            "q-api-autosuggest-self-describe": ("Repair and restoration of bicycles"),
        },
    )

    assert response.status_code == HTTPStatus.FOUND

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

    assert responses["q-api-autosuggest"] == {
        "question_name": "business_activity_question",
        "response_name": ("q-api-autosuggest-self-describe"),
        "value": "Repair and restoration of bicycles",
    }


def test_api_autosuggest_requires_self_description(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that Not listed requires a description."""
    _authenticate(client)
    _enable_autosuggest_self_describe(api_autosuggest_page)
    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    response = client.post(
        "/survey/questions/q-api-autosuggest",
        data={
            "business-activity": "",
            "business-activity-not-listed": "not-listed",
            "q-api-autosuggest-self-describe": "   ",
        },
    )

    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Enter your organisation activity" in response_text
    assert 'id="q-api-autosuggest-self-describe"' in response_text


def test_api_autosuggest_repopulates_self_description(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that a saved self-description is repopulated."""
    _authenticate(client)
    _enable_autosuggest_self_describe(api_autosuggest_page)
    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q-api-autosuggest": {
                "question_name": ("business_activity_question"),
                "response_name": ("q-api-autosuggest-self-describe"),
                "value": "Bicycle repair",
            }
        }

    response = client.get("/survey/questions/q-api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Bicycle repair" in response_text
    assert "Describe your organisation activity" in response_text


def test_api_autosuggest_rejects_empty_response_when_not_listed_disabled(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that Not listed cannot bypass required validation when disabled."""
    _authenticate(client)
    _insert_autosuggest_page(app, api_autosuggest_page)

    response = client.post(
        "/survey/questions/q-api-autosuggest",
        data={
            "business-activity": "",
            "business-activity-not-listed": "not-listed",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_final_survey_page_redirects_to_feedback(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that enabled feedback follows the survey journey."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Teacher",
            }
        }

    response = client.post(
        "/survey/questions/q2",
        data={
            "job-description": "Teaching pupils",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/feedback/fq1")


def test_feedback_response_is_stored_separately(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that feedback does not modify survey responses."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.post(
        "/survey/feedback/fq1",
        data={"survey-ease": "easy"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/feedback/fq2")

    with client.session_transaction() as flask_session:
        assert flask_session[SURVEY_RESPONSES_KEY]["q0"]["value"] == "25-34"
        assert flask_session[SURVEY_FEEDBACK_RESPONSES_KEY]["fq1"] == {
            "question_name": "survey_ease_question",
            "response_name": "survey-ease",
            "value": "easy",
        }


def test_optional_feedback_text_can_be_skipped(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that optional text feedback can be submitted empty."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq2": {
                "question_name": "other_feedback_question",
                "response_name": "other-feedback",
                "value": "Previously entered feedback",
            }
        }

    response = client.post(
        "/survey/feedback/fq2",
        data={"other-feedback": ""},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/complete")

    with client.session_transaction() as flask_session:
        feedback_responses = flask_session.get(
            SURVEY_FEEDBACK_RESPONSES_KEY,
            {},
        )

    assert "fq2" not in feedback_responses


def test_optional_feedback_textarea_is_not_required(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that optional feedback text omits the required attribute."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    response = client.get("/survey/feedback/fq2")
    response_text = response.get_data(as_text=True)

    textarea_start = response_text.index("<textarea")
    textarea_end = response_text.index(">", textarea_start)
    textarea_tag = response_text[textarea_start : textarea_end + 1]

    assert response.status_code == HTTPStatus.OK
    assert 'name="other-feedback"' in textarea_tag
    assert "required" not in textarea_tag


def test_guidance_page_renders(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that a configured guidance page renders."""
    _authenticate(client)
    _insert_guidance_page(
        app,
        guidance_page,
        index=1,
    )

    response = client.get("/survey/guidance/g1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "Describing your work" in response_text
    assert "The next questions ask about" in response_text
    assert "Continue" in response_text


def test_question_redirects_to_following_guidance(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that question progression supports guidance."""
    _authenticate(client)
    _insert_guidance_page(
        app,
        guidance_page,
        index=1,
    )

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "16-24"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/guidance/g1")


def test_guidance_links_to_following_question(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that guidance continues to the next question."""
    _authenticate(client)
    _insert_guidance_page(
        app,
        guidance_page,
        index=1,
    )

    response = client.get("/survey/guidance/g1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/questions/q1" in response_text


def test_final_guidance_links_to_feedback(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that final guidance continues to enabled feedback."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_pages"]["pages"].append(guidance_page)
    survey_definition["survey_feedback"] = survey_feedback

    response = client.get("/survey/guidance/g1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/feedback/fq1" in response_text


def test_final_guidance_links_to_completion(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that final guidance continues to completion."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_pages"]["pages"].append(guidance_page)

    response = client.get("/survey/guidance/g1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/complete" in response_text


def test_paid_job_no_routes_to_survey_feedback_guidance(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that no paid job skips to survey feedback guidance."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    pages = survey_definition["survey_pages"]["pages"]

    paid_job_page: QuestionPage = {
        "page_id": "q-paid-job",
        "page_type": "question",
        "page_title": "Paid Job",
        "question_name": "paid_job_question",
        "question": {
            "text": "Did you have a paid job?",
        },
        "answer": {
            "type": "radio",
            "name": "paid-job",
            "required": True,
            "options": [
                {
                    "id": "paid-job-yes",
                    "label": "Yes",
                    "value": "yes",
                },
                {
                    "id": "paid-job-no",
                    "label": "No",
                    "value": "no",
                    "target_page_id": "g2",
                },
            ],
        },
        "submit_button": {
            "text": "Save and continue",
        },
    }

    target_guidance = dict(guidance_page)
    target_guidance["page_id"] = "g2"

    pages.extend(
        [
            paid_job_page,
            target_guidance,
        ]
    )

    response = client.post(
        "/survey/questions/q-paid-job",
        data={"paid-job": "no"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/guidance/g2")


def test_radio_response_routes_to_target_question(
    app: Flask,
    client: FlaskClient,
) -> None:
    """Test that a radio option can skip to a later question."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    first_page = cast(
        dict[str, object],
        survey_definition["survey_pages"]["pages"][0],
    )
    answer = cast(
        dict[str, object],
        first_page["answer"],
    )
    options = cast(
        list[dict[str, object]],
        answer["options"],
    )
    options[0]["target_page_id"] = "q2"

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "16-24"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q2")


def test_radio_response_routes_to_target_guidance(
    app: Flask,
    client: FlaskClient,
    guidance_page: GuidancePage,
) -> None:
    """Test that a radio option can skip to later guidance."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    pages = survey_definition["survey_pages"]["pages"]
    pages.insert(2, guidance_page)

    first_page = cast(
        dict[str, object],
        pages[0],
    )
    answer = cast(
        dict[str, object],
        first_page["answer"],
    )
    options = cast(
        list[dict[str, object]],
        answer["options"],
    )
    options[1]["target_page_id"] = "g1"

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "25-34"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/guidance/g1")


def test_feedback_radio_routes_to_target_question(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that feedback radio routing skips intermediate feedback."""
    _authenticate(client)
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )

    first_feedback_page = survey_feedback["pages"][0]
    first_answer = cast(
        dict[str, object],
        first_feedback_page["answer"],
    )
    options = cast(
        list[dict[str, object]],
        first_answer["options"],
    )
    options[0]["target_page_id"] = "fq3"

    survey_feedback["pages"].append(
        {
            "page_id": "fq3",
            "page_type": "question",
            "page_title": "Final feedback",
            "question_name": "final_feedback_question",
            "question": {
                "text": "Would you use this survey again?",
            },
            "answer": {
                "type": "radio",
                "name": "use-again",
                "required": True,
                "options": [
                    {
                        "id": "use-again-yes",
                        "label": "Yes",
                        "value": "yes",
                    },
                    {
                        "id": "use-again-no",
                        "label": "No",
                        "value": "no",
                    },
                ],
            },
            "submit_button": {
                "text": "Submit feedback",
            },
        }
    )
    survey_definition["survey_feedback"] = survey_feedback

    response = client.post(
        "/survey/feedback/fq1",
        data={"survey-ease": "easy"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/feedback/fq3")


def _insert_multi_text_page(
    app: Flask,
    page: QuestionPage,
    index: int = 0,
) -> None:
    """Insert a multi-text question into the survey.

    Args:
        app: Configured Flask application.
        page: Multi-text page to insert.
        index: Position at which to insert the page. Defaults to 0.
    """
    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )

    survey_definition["survey_pages"]["pages"].insert(
        index,
        page,
    )


def test_multi_text_question_renders_configured_fields(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test that configured multi-text inputs are rendered."""
    _authenticate(client)
    _insert_multi_text_page(
        app,
        multi_text_page,
    )

    response = client.get(
        "/survey/questions/q-about-you",
    )
    response_text = response.get_data(
        as_text=True,
    )

    assert response.status_code == HTTPStatus.OK
    assert "Enter your details" in response_text

    assert "My First or Given name" in response_text
    assert 'name="first-name"' in response_text

    assert "My Middle Names" in response_text
    assert 'name="middle-names"' in response_text

    assert "My Surname or Family Name" in response_text
    assert 'name="surname"' in response_text


def test_multi_text_response_is_saved_and_progresses(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test that multi-text values are stored and journey continues."""
    _authenticate(client)
    _insert_multi_text_page(
        app,
        multi_text_page,
    )

    response = client.post(
        "/survey/questions/q-about-you",
        data={
            "first-name": " Ada ",
            "middle-names": "",
            "surname": " Lovelace ",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q0")

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

    assert responses["q-about-you"] == {
        "question_name": "about_you_question",
        "values": {
            "first-name": "Ada",
            "middle-names": "",
            "surname": "Lovelace",
        },
    }


def test_multi_text_required_field_returns_bad_request_and_repopulates(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test required multi-text validation retains entered values."""
    _authenticate(client)
    _insert_multi_text_page(
        app,
        multi_text_page,
    )

    response = client.post(
        "/survey/questions/q-about-you",
        data={
            "first-name": "",
            "middle-names": "Augusta",
            "surname": "Lovelace",
        },
    )

    response_text = response.get_data(
        as_text=True,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Enter your first or given name" in response_text
    assert 'value="Augusta"' in response_text
    assert 'value="Lovelace"' in response_text


def test_multi_text_saved_values_are_repopulated(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test that saved multi-text values are rendered again."""
    _authenticate(client)
    _insert_multi_text_page(
        app,
        multi_text_page,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q-about-you": {
                "question_name": "about_you_question",
                "values": {
                    "first-name": "Ada",
                    "middle-names": "Augusta",
                    "surname": "Lovelace",
                },
            }
        }

    response = client.get(
        "/survey/questions/q-about-you",
    )
    response_text = response.get_data(
        as_text=True,
    )

    assert response.status_code == HTTPStatus.OK
    assert 'value="Ada"' in response_text
    assert 'value="Augusta"' in response_text
    assert 'value="Lovelace"' in response_text


def test_first_question_does_not_render_previous_link(
    client: FlaskClient,
) -> None:
    """Test that the first survey question has no previous link."""
    _authenticate(client)

    response = client.get("/survey/questions/q0")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/questions/q0/previous" not in response_text


def test_question_renders_previous_link(
    client: FlaskClient,
) -> None:
    """Test that a later survey question has a previous link."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.get("/survey/questions/q1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/questions/q1/previous" in response_text
    assert "Previous" in response_text


def test_previous_question_discards_current_response(
    client: FlaskClient,
) -> None:
    """Test that going back discards the current survey response."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            },
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Teacher",
            },
        }

    response = client.get("/survey/questions/q1/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q0")

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

    assert "q0" in responses
    assert "q1" not in responses


def test_previous_link_remains_after_survey_validation_error(
    client: FlaskClient,
) -> None:
    """Test that previous remains available after survey validation fails."""
    _authenticate(client)

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.post(
        "/survey/questions/q1",
        data={"job-title": ""},
    )

    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "/survey/questions/q1/previous" in response_text


def test_previous_link_remains_after_feedback_validation_error(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that previous remains available after feedback validation fails."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )

    second_feedback_page = survey_feedback["pages"][1]
    assert second_feedback_page["page_id"] == "fq2"
    second_feedback_page["answer"]["required"] = True

    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq1": {
                "question_name": "survey_ease_question",
                "response_name": "survey-ease",
                "value": "easy",
            }
        }

    response = client.post(
        "/survey/feedback/fq2",
        data={"other-feedback": ""},
    )

    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "/survey/feedback/fq2/previous" in response_text


def test_first_feedback_question_does_not_render_previous_link(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that the first feedback question has no previous link."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    response = client.get("/survey/feedback/fq1")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/feedback/fq1/previous" not in response_text


def test_feedback_question_renders_previous_link(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that a later feedback question renders a previous link."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq1": {
                "question_name": "survey_ease_question",
                "response_name": "survey-ease",
                "value": "easy",
            }
        }

    response = client.get("/survey/feedback/fq2")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/feedback/fq2/previous" in response_text
    assert "Previous" in response_text


def test_previous_feedback_question_discards_current_response(
    app: Flask,
    client: FlaskClient,
    survey_feedback: SurveyFeedback,
) -> None:
    """Test that previous discards the current feedback response."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    survey_definition["survey_feedback"] = survey_feedback

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq1": {
                "question_name": "survey_ease_question",
                "response_name": "survey-ease",
                "value": "easy",
            },
            "fq2": {
                "question_name": "other_feedback_question",
                "response_name": "other-feedback",
                "value": "More guidance would help",
            },
        }

    response = client.get("/survey/feedback/fq2/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/feedback/fq1")

    with client.session_transaction() as flask_session:
        feedback_responses = flask_session[SURVEY_FEEDBACK_RESPONSES_KEY]

    assert "fq1" in feedback_responses
    assert "fq2" not in feedback_responses


def test_previous_question_returns_to_answered_question_after_skip(
    app: Flask,
    client: FlaskClient,
) -> None:
    """Test that previous follows the answered journey after a routing skip."""
    _authenticate(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )
    first_page = cast(
        dict[str, object],
        survey_definition["survey_pages"]["pages"][0],
    )
    answer = cast(
        dict[str, object],
        first_page["answer"],
    )
    options = cast(
        list[dict[str, object]],
        answer["options"],
    )
    options[0]["target_page_id"] = "q2"

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "16-24"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q2")

    response = client.get("/survey/questions/q2/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q0")


def test_api_autosuggest_renders_previous_link(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test that API autosuggest renders previous navigation."""
    _authenticate(client)
    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.get("/survey/questions/q-api-autosuggest")
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "/survey/questions/q-api-autosuggest/previous" in response_text


def test_api_autosuggest_previous_link_remains_after_self_describe_error(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test previous remains available after autosuggest validation fails."""
    _authenticate(client)
    _enable_autosuggest_self_describe(
        api_autosuggest_page,
    )
    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.post(
        "/survey/questions/q-api-autosuggest",
        data={
            "business-activity": "",
            "business-activity-not-listed": "not-listed",
            "q-api-autosuggest-self-describe": "",
        },
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "/survey/questions/q-api-autosuggest/previous" in response_text


def test_multi_text_validation_keeps_previous_link(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test previous remains available after multi-text validation fails."""
    _authenticate(client)
    _insert_multi_text_page(
        app,
        multi_text_page,
        index=1,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            }
        }

    response = client.post(
        "/survey/questions/q-about-you",
        data={
            "first-name": "",
            "middle-names": "Augusta",
            "surname": "Lovelace",
        },
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "/survey/questions/q-about-you/previous" in response_text


def test_previous_question_discards_multi_text_response(
    app: Flask,
    client: FlaskClient,
    multi_text_page: QuestionPage,
) -> None:
    """Test previous navigation discards a multi-text response."""
    _authenticate(client)

    _insert_multi_text_page(
        app,
        multi_text_page,
        index=1,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "25-34",
            },
            "q-about-you": {
                "question_name": "about_you_question",
                "values": {
                    "first-name": "Ada",
                    "middle-names": "Augusta",
                    "surname": "Lovelace",
                },
            },
        }

    response = client.get("/survey/questions/q-about-you/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q0")

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

    assert "q0" in responses
    assert "q-about-you" not in responses


def test_conditional_question_text_updates_after_navigating_back(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Test conditional question text updates after changing a previous answer."""
    _authenticate(client)

    api_autosuggest_page["question"]["text"] = "What is the main activity of PLACEHOLDER_TEXT?"
    api_autosuggest_page["question"]["placeholders"] = [
        {
            "placeholder": "PLACEHOLDER_TEXT",
            "source_question_name": "age_range_question",
            "value_map": {
                "16-24": "the younger group",
                "25-34": "the older group",
            },
        }
    ]

    _insert_autosuggest_page(
        app,
        api_autosuggest_page,
    )

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "question_name": "age_range_question",
                "response_name": "age-range",
                "value": "16-24",
            },
            "q-api-autosuggest": {
                "question_name": "business_activity_question",
                "response_name": "business-activity",
                "value": "Software development",
            },
        }

    response = client.get(
        "/survey/questions/q-api-autosuggest/previous",
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith(
        "/survey/questions/q0",
    )

    response = client.post(
        "/survey/questions/q0",
        data={"age-range": "25-34"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith(
        "/survey/questions/q-api-autosuggest",
    )

    response = client.get(
        "/survey/questions/q-api-autosuggest",
    )
    response_text = response.get_data(as_text=True)

    assert response.status_code == HTTPStatus.OK
    assert "What is the main activity of the older group?" in response_text
    assert "the younger group" not in response_text


def test_submit_result_question_sends_result_before_continuing(
    client: FlaskClient,
    app: Flask,
) -> None:
    """Test a configured question submits a survey result."""
    _authenticate(client)
    _set_result_session(client)

    survey_definition = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )

    page = cast(
        QuestionPage,
        survey_definition["survey_pages"]["pages"][2],
    )
    page["submit_result"] = True

    result_client = StubSurveyResultSubmissionClient()
    app.extensions["result_submission_client"] = result_client

    with client.session_transaction() as flask_session:
        flask_session[SURVEY_RESPONSES_KEY] = {
            "q1": {
                "question_name": "job_title_question",
                "response_name": "job-title",
                "value": "Primary school teacher",
            }
        }

    response = client.post(
        "/survey/questions/q2",
        data={"job-description": ("I plan lessons and teach primary school pupils.")},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert len(result_client.submitted_results) == 1

    result = result_client.submitted_results[0]

    assert result.survey_id == "test_survey"
    assert result.wave_id == "test-wave"
    assert result.user == "11-01"
    assert result.case_id == "11"

    assert result.time_start == datetime(
        2026,
        9,
        25,
        9,
        0,
        tzinfo=UTC,
    )

    assert result.responses[0].person_id == "11-01"
    assert result.responses[0].time_start == datetime(
        2026,
        9,
        25,
        9,
        5,
        tzinfo=UTC,
    )

    assert result.responses[0].time_end == result.time_end


def test_question_without_submit_result_does_not_send_result(
    client: FlaskClient,
    app: Flask,
) -> None:
    """Test normal questions do not submit survey results."""
    _authenticate(client)
    _set_result_session(client)

    result_client = StubSurveyResultSubmissionClient()
    app.extensions["result_submission_client"] = result_client

    client.post(
        "/survey/questions/q0",
        data={"age-range": "25-34"},
    )

    assert not result_client.submitted_results


def test_first_survey_page_records_response_start_time(
    client: FlaskClient,
) -> None:
    """Test entering survey_pages records its start timestamp."""
    _authenticate(client)

    client.get("/survey/questions/q0")

    with client.session_transaction() as flask_session:
        timestamp = datetime.fromisoformat(flask_session[SURVEY_RESPONSE_START_TIME_KEY])

    assert timestamp.tzinfo is not None
