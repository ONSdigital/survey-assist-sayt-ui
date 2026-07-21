"""Shared pytest fixtures for the Survey Assist SAYT UI."""

from collections.abc import Callable, Iterator

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.app import create_app
from survey_assist_sayt_ui.auth.service import AuthService, AuthStore
from survey_assist_sayt_ui.config import Settings
from survey_assist_sayt_ui.survey.models import (
    QuestionPage,
    SurveyDefinition,
    SurveyFeedback,
)

TokenRefresher = Callable[[int, str, str, str], tuple[int, str]]


class StaticAuthStore(AuthStore):  # pylint: disable=too-few-public-methods
    """Provide a fixed set of authentication users for tests."""

    def __init__(self, users: dict[str, str] | None = None) -> None:
        """Initialise the test authentication store.

        Args:
            users: Optional mapping of usernames to password hashes.
        """
        self.users = users or {}

    def load_users(self) -> dict[str, str]:
        """Return the configured users.

        Returns:
            dict[str, str]: Configured username and password hash mapping.
        """
        return self.users


def _static_token_refresher(
    token_start_time: int,
    current_token: str,
    api_gateway: str,
    sa_email: str,
) -> tuple[int, str]:
    """Return a deterministic token without contacting Google IAM."""
    assert api_gateway == "0.0.0.0:8080"
    assert sa_email == "sayt-ui@example.iam.gserviceaccount.com"

    return (
        token_start_time or 1_700_000_000,
        current_token or "test-jwt-token",
    )


@pytest.fixture
def static_token_refresher() -> TokenRefresher:
    """Provide a deterministic token refresher for tests."""
    return _static_token_refresher


@pytest.fixture(name="survey_definition")
def survey_definition_fixture() -> SurveyDefinition:
    """Provide a valid two-question survey definition.

    Returns:
        SurveyDefinition: Survey containing one radio and one text question.
    """
    return {
        "schema_version": 1,
        "survey_title": "Test survey",
        "wave_id": "test-wave",
        "survey_intro": {
            "enabled": True,
            "intro": {
                "navigation": {
                    "header": "In this section",
                    "aria_label": "Sections in this page",
                    "entries": [
                        {
                            "link": "#begin-study",
                            "text": "Begin study",
                        }
                    ],
                },
                "sections": [
                    {
                        "id": "begin-study",
                        "heading": "Begin study",
                        "blocks": [],
                    }
                ],
            },
        },
        "survey_pages": {
            "enabled": True,
            "start_page_id": "q0",
            "pages": [
                {
                    "page_id": "q0",
                    "page_type": "question",
                    "page_title": "Age Range",
                    "question_name": "age_range_question",
                    "question": {
                        "text": "Select your age range from the options below",
                    },
                    "answer": {
                        "type": "radio",
                        "name": "age-range",
                        "required": True,
                        "options": [
                            {
                                "id": "age-range-16-24",
                                "label": "16-24",
                                "value": "16-24",
                            },
                            {
                                "id": "age-range-25-34",
                                "label": "25-34",
                                "value": "25-34",
                            },
                        ],
                    },
                    "submit_button": {
                        "text": "Save and continue",
                    },
                },
                {
                    "page_id": "q1",
                    "page_type": "question",
                    "page_title": "Job Title",
                    "question_name": "job_title_question",
                    "question": {
                        "text": ("What is the exact job title for your main " "job or business?"),
                    },
                    "answer": {
                        "type": "text",
                        "name": "job-title",
                        "required": True,
                        "multiline": True,
                        "rows": 5,
                        "character_limit": 150,
                    },
                    "submit_button": {
                        "text": "Save and continue",
                    },
                },
                {
                    "page_id": "q2",
                    "page_type": "question",
                    "page_title": "Job Description",
                    "question_name": "job_description_question",
                    "question": {
                        "text": (
                            "Describe what you do in that job or business as a " "PLACEHOLDER_TEXT"
                        ),
                        "placeholders": [
                            {
                                "placeholder": "PLACEHOLDER_TEXT",
                                "source_question_name": "job_title_question",
                            }
                        ],
                    },
                    "answer": {
                        "type": "text",
                        "name": "job-description",
                        "required": True,
                        "multiline": True,
                        "rows": 8,
                        "character_limit": 500,
                    },
                    "submit_button": {
                        "text": "Save and continue",
                    },
                },
            ],
        },
    }


@pytest.fixture(name="question_page")
def question_page_fixture() -> QuestionPage:
    """Provide a question page containing a response placeholder.

    Returns:
        QuestionPage: Job-description question referencing the job-title
            response.
    """
    return {
        "page_id": "q2",
        "page_type": "question",
        "page_title": "Job Description",
        "question_name": "job_description_question",
        "question": {
            "text": ("Describe what you do in that job or business as a " "PLACEHOLDER_TEXT"),
            "placeholders": [
                {
                    "placeholder": "PLACEHOLDER_TEXT",
                    "source_question_name": "job_title_question",
                }
            ],
        },
        "answer": {
            "type": "text",
            "name": "job-description",
            "required": True,
            "multiline": True,
            "rows": 8,
            "character_limit": 500,
        },
        "submit_button": {
            "text": "Save and continue",
        },
    }


@pytest.fixture(name="api_autosuggest_page")
def api_autosuggest_page_fixture() -> QuestionPage:
    """Provide an API-backed autosuggest question page.

    Returns:
        QuestionPage: Business-activity autosuggest question.
    """
    return {
        "page_id": "q-api-autosuggest",
        "page_type": "question",
        "page_title": "Business Activity",
        "question_name": "business_activity_question",
        "question": {
            "text": ("What is the main activity of the business " "or freelance work?"),
        },
        "answer": {
            "type": "api_autosuggest",
            "name": "business-activity",
            "required": True,
            "placeholder": "Type the main activity",
        },
        "submit_button": {
            "text": "Save and continue",
        },
    }


@pytest.fixture(name="survey_feedback")
def survey_feedback_fixture() -> SurveyFeedback:
    """Provide a valid two-page feedback journey.

    Returns:
        SurveyFeedback: Radio and optional text feedback pages.
    """
    return {
        "enabled": True,
        "start_page_id": "fq1",
        "pages": [
            {
                "page_id": "fq1",
                "page_type": "question",
                "page_title": "Survey Ease",
                "question_name": "survey_ease_question",
                "question": {
                    "text": ("In general, how easy or difficult " "did you find this survey?"),
                },
                "answer": {
                    "type": "radio",
                    "name": "survey-ease",
                    "required": True,
                    "options": [
                        {
                            "id": "survey-ease-easy",
                            "label": "Easy",
                            "value": "easy",
                        },
                        {
                            "id": "survey-ease-difficult",
                            "label": "Difficult",
                            "value": "difficult",
                        },
                    ],
                },
                "submit_button": {
                    "text": "Save and continue",
                },
            },
            {
                "page_id": "fq2",
                "page_type": "question",
                "page_title": "Other Feedback",
                "question_name": "other_feedback_question",
                "question": {
                    "text": ("Do you have any other feedback " "about this survey?"),
                },
                "answer": {
                    "type": "text",
                    "name": "other-feedback",
                    "required": False,
                    "multiline": True,
                    "rows": 5,
                    "character_limit": 500,
                },
                "submit_button": {
                    "text": "Submit feedback",
                },
            },
        ],
    }


@pytest.fixture(name="app")
def app_fixture(
    static_token_refresher: TokenRefresher,  # pylint: disable=redefined-outer-name
    survey_definition: SurveyDefinition,
) -> Flask:
    """Create a configured Flask application for tests.

    Args:
        static_token_refresher: Deterministic JWT token refresher.
        survey_definition: Survey definition used by route tests.

    Returns:
        Flask: Test application instance.
    """
    settings = Settings(
        secret_key="test-secret-key",  # pragma: allowlist secret
        sayt_api_url="http://0.0.0.0:8080/v1/survey-assist/sic-lookup",
        sa_email="sayt-ui@example.iam.gserviceaccount.com",
        service_name="Survey Assist SAYT UI",
        auth_mode="local",
        session_cookie_secure=False,
    )

    application = create_app(
        settings=settings,
        auth_service=AuthService(StaticAuthStore()),
        survey_definition=survey_definition,
        token_refresher=static_token_refresher,
    )
    application.config.update(TESTING=True)

    return application


@pytest.fixture(name="client")
def client_fixture(app: Flask) -> Iterator[FlaskClient]:
    """Create a Flask test client.

    Args:
        app: Configured Flask application.

    Yields:
        FlaskClient: Client for making test HTTP requests.
    """
    with app.test_client() as test_client:
        yield test_client
