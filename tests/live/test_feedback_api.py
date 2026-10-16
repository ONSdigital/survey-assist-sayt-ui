"""Store survey feedback through the hosted Survey Assist API.

Run with RUN_SURVEY_ASSIST_API_TEST=1. The normal test command skips this.
"""

from datetime import UTC, datetime
from http import HTTPStatus
import os
import re
from uuid import uuid4

from dotenv import load_dotenv
import pytest

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_RESULT_USER_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.routes.survey import SURVEY_FEEDBACK_RESPONSES_KEY
from survey_assist_sayt_ui.services.survey_assist_api import SurveyAssistApiClient

load_dotenv()

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SURVEY_ASSIST_API_TEST") != "1",
    reason="Set RUN_SURVEY_ASSIST_API_TEST=1 to store feedback through the API.",
)


def test_completion_page_stores_feedback_on_the_api() -> None:
    """The completion page saves session feedback and the API returns it."""
    app = create_app()
    app.config.update(TESTING=True)
    wave_id = f"sa-1025-{uuid4().hex[:12]}"
    survey_definition = app.extensions["survey_definition"]
    survey_definition["wave_id"] = wave_id
    person_id = f"live-{uuid4().hex[:8]}"
    survey_id = re.sub(r"\s+", "_", survey_definition["survey_title"].strip().lower())

    client = app.test_client()
    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()
        flask_session[SESSION_RESULT_USER_KEY] = person_id
        flask_session[SURVEY_FEEDBACK_RESPONSES_KEY] = {
            "fq1": {
                "question_name": "survey_ease_question",
                "response_name": "survey-ease",
                "value": "easy",
            }
        }

    response = client.get("/survey/complete")

    assert response.status_code == HTTPStatus.OK
    assert "Thank you for taking part." in response.get_data(as_text=True)

    api_client = app.extensions["survey_assist_api_client"]
    assert isinstance(api_client, SurveyAssistApiClient)
    stored = api_client.get(
        "feedbacks",
        params={
            "survey_id": survey_id,
            "wave_id": wave_id,
            "case_id": person_id.split("-", maxsplit=1)[0],
        },
    ).json()

    assert stored["count"] == 1
    saved = stored["results"][0]
    assert saved["person_id"] == person_id
    assert saved["wave_id"] == wave_id
    assert saved["questions"][0]["response"] == "easy"
    assert saved["questions"][0]["response_name"] == "survey-ease"
    assert saved["questions"][0]["response_options"] == [
        "Very easy",
        "Easy",
        "Neither easy or difficult",
        "Difficult",
        "Very difficult",
    ]
