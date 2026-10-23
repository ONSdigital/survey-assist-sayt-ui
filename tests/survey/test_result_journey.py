"""Integration tests for SAYT suggestion result submission."""

from datetime import UTC, datetime
from http import HTTPStatus
import json
from typing import cast

from flask import Flask
from flask.testing import FlaskClient
import pytest

from survey_assist_sayt_ui.auth.decorators import (
    SESSION_LOGIN_TIME_KEY,
    SESSION_RESULT_USER_KEY,
    SESSION_USER_KEY,
)
from survey_assist_sayt_ui.models.result import (
    ResultResponse,
    SuggestionInteraction,
    SurveyAssistResult,
)
from survey_assist_sayt_ui.survey.models import (
    ApiAutosuggestAnswer,
    QuestionPage,
    SurveyDefinition,
)
from survey_assist_sayt_ui.survey.session import (
    QUESTION_RENDER_TIME_KEY,
    SUGGESTION_TIME_END_KEY,
    SUGGESTION_TIME_START_KEY,
    SURVEY_RESPONSES_KEY,
)

SAYT_PAGE_ID = "q-api-autosuggest"
SAYT_URL = f"/survey/questions/{SAYT_PAGE_ID}"

DISPLAYED_SUGGESTIONS = [
    "Electrical installation",
    "Electrical wholesaler",
    "Electrical equipment repair",
]

QUERY_HISTORY = [
    {
        "value": "electrical",
        "time_start": "2026-10-16T09:01:04+00:00",
        "time_end": "2026-10-16T09:01:05+00:00",
    },
    {
        "value": "electri",
        "time_start": "2026-10-16T09:01:02+00:00",
        "time_end": "2026-10-16T09:01:03+00:00",
    },
    {
        "value": "electr",
        "time_start": "2026-10-16T09:01:00+00:00",
        "time_end": "2026-10-16T09:01:01+00:00",
    },
]


class StubResultClient:  # pylint: disable=too-few-public-methods
    """Capture submitted result payloads without calling the API."""

    def __init__(self) -> None:
        self.submitted_results: list[SurveyAssistResult] = []

    def submit(self, result: SurveyAssistResult) -> ResultResponse:
        """Store and acknowledge a result."""
        self.submitted_results.append(result)
        return ResultResponse(
            message="Result stored successfully",
            result_id="result-123",
        )


def configure_journey(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
    *,
    submit_page_id: str,
    enable_not_listed: bool = False,
) -> StubResultClient:
    """Configure the survey and its result submission stub."""
    survey = cast(
        SurveyDefinition,
        app.extensions["survey_definition"],
    )

    if enable_not_listed:
        answer = cast(
            ApiAutosuggestAnswer,
            api_autosuggest_page["answer"],
        )
        answer["not_listed"] = True
        answer["self_describe"] = {
            "label": "Describe your activity",
            "required_error": "Enter your activity",
        }

    survey["survey_pages"]["pages"].insert(
        1,
        api_autosuggest_page,
    )

    for page in survey["survey_pages"]["pages"]:
        if page["page_type"] == "question":
            page["submit_result"] = page["page_id"] == submit_page_id

    result_client = StubResultClient()
    app.extensions["result_submission_client"] = result_client

    with client.session_transaction() as flask_session:
        flask_session[SESSION_USER_KEY] = "person@example.com"
        flask_session[SESSION_RESULT_USER_KEY] = "11-01"
        flask_session[SESSION_LOGIN_TIME_KEY] = datetime.now(UTC).isoformat()

    return result_client


def render_question(
    client: FlaskClient,
    page_id: str,
) -> datetime:
    """Render a question and return its recorded server timestamp."""
    response = client.get(f"/survey/questions/{page_id}")

    assert response.status_code == HTTPStatus.OK

    with client.session_transaction() as flask_session:
        return datetime.fromisoformat(flask_session[QUESTION_RENDER_TIME_KEY])


def save_question(
    client: FlaskClient,
    page_id: str,
    data: dict[str, str],
) -> None:
    """Save a valid question response."""
    response = client.post(
        f"/survey/questions/{page_id}",
        data=data,
    )
    assert response.status_code == HTTPStatus.FOUND


def answer_sayt(
    client: FlaskClient,
    *,
    selected: str = "Electrical installation",
    suggestions: list[str] | None = None,
    queries: list[dict[str, str]] | None = None,
    not_listed_description: str | None = None,
) -> tuple[datetime, datetime]:
    """Answer SAYT and return its server-side start/end timestamps."""
    start = render_question(client, SAYT_PAGE_ID)

    data = {
        "business-activity": selected,
        "business-activity-selected": selected,
        "business-activity-suggestions": json.dumps(
            DISPLAYED_SUGGESTIONS if suggestions is None else suggestions
        ),
        "business-activity-queries": json.dumps(QUERY_HISTORY if queries is None else queries),
    }

    if not_listed_description is not None:
        data["business-activity"] = ""
        data["business-activity-selected"] = ""
        data["business-activity-not-listed"] = "not-listed"
        data["q-api-autosuggest-self-describe"] = not_listed_description

    save_question(client, SAYT_PAGE_ID, data)

    with client.session_transaction() as flask_session:
        end = datetime.fromisoformat(flask_session[SUGGESTION_TIME_END_KEY])

    return start, end


def get_interaction(
    result_client: StubResultClient,
) -> SuggestionInteraction:
    """Return the sole submitted suggestion interaction."""
    assert len(result_client.submitted_results) == 1

    result = result_client.submitted_results[0]
    assert len(result.responses) == 1

    interactions = result.responses[0].survey_assist_interactions
    assert len(interactions) == 1

    interaction = interactions[0]
    assert isinstance(interaction, SuggestionInteraction)

    return interaction


@pytest.mark.parametrize(
    "submit_page_id",
    [
        SAYT_PAGE_ID,
        "q2",
    ],
)
def test_result_on_or_after_sayt_preserves_interaction(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
    submit_page_id: str,
) -> None:
    """Verify inputs, SAYT timestamps, selection, queries and list order."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id=submit_page_id,
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    sayt_start, sayt_end = answer_sayt(client)

    if submit_page_id == "q2":
        render_question(client, "q1")
        save_question(
            client,
            "q1",
            {
                "job-title": "Electrician",
            },
        )
        render_question(client, "q2")
        save_question(
            client,
            "q2",
            {
                "job-description": "Install electrical wiring",
            },
        )

    interaction = get_interaction(result_client)

    assert interaction.time_start == sayt_start
    assert interaction.time_end == sayt_end
    assert interaction.time_end >= interaction.time_start

    expected_inputs = [
        ("age-range", "25-34"),
        ("business-activity", "Electrical installation"),
    ]

    if submit_page_id == "q2":
        expected_inputs.extend(
            [
                ("job-title", "Electrician"),
                ("job-description", "Install electrical wiring"),
            ]
        )

    assert [(item.field, item.value) for item in interaction.input] == expected_inputs

    assert interaction.response.listed is True
    assert interaction.response.code == "99999"
    assert interaction.response.description == "Electrical installation"
    assert interaction.response.not_listed_description == ""

    # Only the last displayed list is included, in its original order.
    assert [(item.code, item.description) for item in interaction.response.suggestions] == [
        ("99999", "Electrical installation"),
        ("99999", "Electrical wholesaler"),
        ("99999", "Electrical equipment repair"),
    ]

    # Query history is newest first and has the supplied server timestamps.
    assert interaction.queries_sent == 3

    assert [query.value for query in interaction.queries] == [
        "electrical",
        "electri",
        "electr",
    ]

    for actual, expected in zip(
        interaction.queries,
        QUERY_HISTORY,
        strict=True,
    ):
        assert actual.time_start == datetime.fromisoformat(expected["time_start"])
        assert actual.time_end == datetime.fromisoformat(expected["time_end"])


def test_not_listed_preserves_suggestions_and_queries(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Verify Not Listed retains the last suggestion list and searches."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id=SAYT_PAGE_ID,
        enable_not_listed=True,
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    answer_sayt(
        client,
        not_listed_description="Domestic rewiring services",
    )

    interaction = get_interaction(result_client)

    assert interaction.response.listed is False
    assert interaction.response.code == ""
    assert interaction.response.description == ""
    assert interaction.response.not_listed_description == "Domestic rewiring services"

    assert [item.description for item in interaction.response.suggestions] == DISPLAYED_SUGGESTIONS

    assert interaction.queries_sent == len(QUERY_HISTORY)
    assert len(interaction.queries) == len(QUERY_HISTORY)

    assert (
        "q-api-autosuggest-self-describe",
        "Domestic rewiring services",
    ) in [(item.field, item.value) for item in interaction.input]


def test_empty_search_results_produce_empty_suggestions(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Verify an empty displayed list is retained with query history."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id=SAYT_PAGE_ID,
        enable_not_listed=True,
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    answer_sayt(
        client,
        suggestions=[],
        queries=QUERY_HISTORY[:1],
        not_listed_description="Unlisted business activity",
    )

    interaction = get_interaction(result_client)

    assert interaction.response.suggestions == []
    assert interaction.response.listed is False
    assert interaction.queries_sent == 1
    assert interaction.queries[0].value == "electrical"


def test_navigating_before_sayt_discards_old_interaction(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Verify revisiting SAYT creates a fresh saved interaction."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id="q2",
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    first_start, _ = answer_sayt(client)

    render_question(client, "q1")
    save_question(
        client,
        "q1",
        {
            "job-title": "Electrician",
        },
    )

    render_question(client, "q2")

    # Navigate back from q2 to q1, discarding q1 and q2 answers.
    response = client.get("/survey/questions/q2/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q1")

    # Navigate back from q1 to q0, discarding the SAYT answer.
    response = client.get("/survey/questions/q1/previous")

    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"].endswith("/survey/questions/q0")

    with client.session_transaction() as flask_session:
        responses = flask_session[SURVEY_RESPONSES_KEY]

        assert "q0" in responses
        assert SAYT_PAGE_ID not in responses
        assert "q1" not in responses
        assert "q2" not in responses
        assert SUGGESTION_TIME_START_KEY not in flask_session
        assert SUGGESTION_TIME_END_KEY not in flask_session

    # Start the journey again with different answers and searches.
    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "16-24"})

    second_start, second_end = answer_sayt(
        client,
        selected="Software development",
        suggestions=[
            "Software development",
            "Computer programming",
        ],
        queries=[
            {
                "value": "software",
                "time_start": "2026-10-16T09:10:00+00:00",
                "time_end": "2026-10-16T09:10:01+00:00",
            }
        ],
    )

    render_question(client, "q1")
    save_question(
        client,
        "q1",
        {
            "job-title": "Software developer",
        },
    )

    render_question(client, "q2")
    save_question(
        client,
        "q2",
        {
            "job-description": "Develop software",
        },
    )

    interaction = get_interaction(result_client)

    assert second_start >= first_start
    assert interaction.time_start == second_start
    assert interaction.time_end == second_end

    assert [(item.field, item.value) for item in interaction.input] == [
        ("age-range", "16-24"),
        ("business-activity", "Software development"),
        ("job-title", "Software developer"),
        ("job-description", "Develop software"),
    ]

    assert interaction.response.listed is True
    assert interaction.response.description == "Software development"

    assert [item.description for item in interaction.response.suggestions] == [
        "Software development",
        "Computer programming",
    ]

    assert interaction.queries_sent == 1
    assert [query.value for query in interaction.queries] == ["software"]


def test_reanswering_sayt_uses_latest_saved_suggestions(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Verify re-answering SAYT replaces its previous interaction data."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id="q2",
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    # First SAYT answer and search history.
    answer_sayt(
        client,
        selected="Electrical installation",
        suggestions=[
            "Electrical installation",
            "Electrical wholesaler",
        ],
        queries=QUERY_HISTORY,
    )

    # Revisit SAYT and submit different search results.
    latest_start, latest_end = answer_sayt(
        client,
        selected="Software development",
        suggestions=[
            "Software development",
            "Computer programming",
            "IT consultancy",
        ],
        queries=[
            {
                "value": "software",
                "time_start": "2026-10-16T09:10:00+00:00",
                "time_end": "2026-10-16T09:10:01+00:00",
            },
        ],
    )

    # Submit the result on a later question.
    render_question(client, "q1")
    save_question(
        client,
        "q1",
        {"job-title": "Software developer"},
    )

    render_question(client, "q2")
    save_question(
        client,
        "q2",
        {"job-description": "Develop software"},
    )

    interaction = get_interaction(result_client)

    assert interaction.time_start == latest_start
    assert interaction.time_end == latest_end

    assert interaction.response.listed is True
    assert interaction.response.code == "99999"
    assert interaction.response.description == "Software development"
    assert interaction.response.not_listed_description == ""

    assert [item.description for item in interaction.response.suggestions] == [
        "Software development",
        "Computer programming",
        "IT consultancy",
    ]

    assert interaction.queries_sent == 1
    assert [query.value for query in interaction.queries] == [
        "software",
    ]

    # Confirm the previous SAYT selection is no longer recorded.
    assert (
        "business-activity",
        "Software development",
    ) in [(item.field, item.value) for item in interaction.input]


def test_revisiting_sayt_without_changes_preserves_history(
    app: Flask,
    client: FlaskClient,
    api_autosuggest_page: QuestionPage,
) -> None:
    """Preserve saved SAYT searches when the answer is submitted unchanged."""
    result_client = configure_journey(
        app,
        client,
        api_autosuggest_page,
        submit_page_id="q2",
    )

    render_question(client, "q0")
    save_question(client, "q0", {"age-range": "25-34"})

    # Answer SAYT with an initial selection and search history.
    answer_sayt(client)

    # Move forward to the next question.
    render_question(client, "q1")
    save_question(
        client,
        "q1",
        {"job-title": "Electrician"},
    )

    # Revisit the saved SAYT question without discarding its response.
    response = client.get(SAYT_URL)

    assert response.status_code == HTTPStatus.OK

    # Verify the saved selection and interaction history still exist.
    with client.session_transaction() as flask_session:
        saved = flask_session[SURVEY_RESPONSES_KEY][SAYT_PAGE_ID]

        assert saved["value"] == "Electrical installation"
        assert saved["suggestions"] == DISPLAYED_SUGGESTIONS
        assert saved["queries"] == QUERY_HISTORY

    # Verify the rendered page contains the restored hidden fields.
    response_text = response.get_data(as_text=True)

    assert "Electrical installation" in response_text
    assert "business-activity-suggestions" in response_text
    assert "business-activity-queries" in response_text

    # Simulate submitting the restored fields without a new search.
    save_question(
        client,
        SAYT_PAGE_ID,
        {
            "business-activity": "Electrical installation",
            "business-activity-selected": "Electrical installation",
            "business-activity-suggestions": json.dumps(DISPLAYED_SUGGESTIONS),
            "business-activity-queries": json.dumps(QUERY_HISTORY),
        },
    )

    # Continue to the result submission checkpoint.
    render_question(client, "q1")
    save_question(
        client,
        "q1",
        {"job-title": "Electrician"},
    )

    render_question(client, "q2")
    save_question(
        client,
        "q2",
        {"job-description": "Install electrical wiring"},
    )

    interaction = get_interaction(result_client)

    # Confirm the selected answer is retained.
    assert interaction.response.listed is True
    assert interaction.response.code == "99999"
    assert interaction.response.description == "Electrical installation"
    assert interaction.response.not_listed_description == ""

    # Confirm the saved suggestions are preserved in their original order.
    assert [item.description for item in interaction.response.suggestions] == DISPLAYED_SUGGESTIONS

    # Confirm the original query history is preserved.
    assert interaction.queries_sent == len(QUERY_HISTORY)
    assert [query.value for query in interaction.queries] == [
        query["value"] for query in QUERY_HISTORY
    ]
