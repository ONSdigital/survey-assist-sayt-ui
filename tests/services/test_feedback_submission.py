"""Tests for the Survey Assist feedback submission service."""

from http import HTTPStatus
import json

import httpx
import pytest

from survey_assist_sayt_ui.models.feedback import FeedbackQuestion, FeedbackResult
from survey_assist_sayt_ui.services.feedback_submission import (
    FeedbackSubmissionError,
    FeedbackSubmissionTimeoutError,
    HttpSurveyFeedbackSubmissionClient,
)
from survey_assist_sayt_ui.services.survey_assist_api import SurveyAssistApiClient


def _build_feedback() -> FeedbackResult:
    """Create a sample feedback payload."""
    return FeedbackResult(
        survey_id="test_survey",
        wave_id="test-wave",
        case_id="11",
        person_id="11-01",
        questions=[
            FeedbackQuestion(
                response="easy",
                response_name="survey-ease",
                response_options=["Easy", "Difficult"],
            )
        ],
    )


def _create_client(handler: httpx.MockTransport) -> HttpSurveyFeedbackSubmissionClient:
    """Create a feedback client backed by a mock transport."""
    api_client = SurveyAssistApiClient(
        base_url="https://gateway.example/v1/survey-assist",
        token="test-jwt-token",
        client=httpx.Client(transport=handler),
    )
    return HttpSurveyFeedbackSubmissionClient(api_client)


def test_submit_posts_feedback_and_parses_acknowledgement() -> None:
    """Test submit posts feedback and reads the feedback id."""
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            HTTPStatus.OK,
            json={
                "message": "Feedback stored successfully",
                "feedback_id": "feedback-123",
            },
            request=request,
        )

    acknowledgement = _create_client(httpx.MockTransport(handler)).submit(_build_feedback())

    assert captured_request is not None
    assert str(captured_request.url) == ("https://gateway.example/v1/survey-assist/feedback")
    body = json.loads(captured_request.content)
    assert body["person_id"] == "11-01"
    assert body["questions"][0]["response_options"] == ["Easy", "Difficult"]
    assert acknowledgement.feedback_id == "feedback-123"


def test_submit_does_not_retry_after_timeout() -> None:
    """Test submit raises once when the feedback call times out."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        raise httpx.ReadTimeout("Request timed out", request=request)

    with pytest.raises(FeedbackSubmissionTimeoutError):
        _create_client(httpx.MockTransport(handler)).submit(_build_feedback())

    assert request_count == 1


def test_submit_does_not_retry_after_gateway_timeout() -> None:
    """Test submit raises once when the feedback call returns a gateway timeout."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(HTTPStatus.GATEWAY_TIMEOUT, request=request)

    with pytest.raises(FeedbackSubmissionError):
        _create_client(httpx.MockTransport(handler)).submit(_build_feedback())

    assert request_count == 1


def test_submit_raises_error_for_invalid_acknowledgement() -> None:
    """Test submit raises when the acknowledgement is not valid feedback JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            content=b"not-json",
            request=request,
        )

    with pytest.raises(FeedbackSubmissionError):
        _create_client(httpx.MockTransport(handler)).submit(_build_feedback())
