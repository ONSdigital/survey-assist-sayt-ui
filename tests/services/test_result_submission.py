"""Tests for the Survey Assist result submission service."""

# pylint: disable=duplicate-code
from datetime import UTC, datetime
from http import HTTPStatus
import json

import httpx
import pytest

from survey_assist_sayt_ui.models.result import Response, SurveyAssistResult
from survey_assist_sayt_ui.services.result_submission import (
    HttpSurveyResultSubmissionClient,
    ResultSubmissionError,
    ResultSubmissionTimeoutError,
)
from survey_assist_sayt_ui.services.survey_assist_api import SurveyAssistApiClient


def _build_result() -> SurveyAssistResult:
    """Create a sample survey result for testing.

    Returns:
        SurveyAssistResult: A test survey result with basic fields populated.
    """
    start = datetime(2026, 9, 25, 10, 0, tzinfo=UTC)
    end = datetime(2026, 9, 25, 10, 5, tzinfo=UTC)

    return SurveyAssistResult(
        survey_id="test_survey",
        wave_id="test-wave",
        case_id="test-case",
        user="test-user",
        time_start=start,
        time_end=end,
        responses=[
            Response(
                person_id="test-person",
                time_start=start,
                time_end=end,
                survey_assist_interactions=[],
            )
        ],
    )


def _create_client(
    handler: httpx.MockTransport,
) -> HttpSurveyResultSubmissionClient:
    """Create a result submission client with a mock HTTP transport.

    Args:
        handler: An httpx.MockTransport to handle requests.

    Returns:
        HttpSurveyResultSubmissionClient: A client configured with the mock transport.
    """
    api_client = SurveyAssistApiClient(
        base_url="https://gateway.example/v1/survey-assist",
        token="test-jwt-token",
        client=httpx.Client(transport=handler),
    )
    return HttpSurveyResultSubmissionClient(api_client)


def test_submit_posts_empty_interactions_and_parses_acknowledgement() -> None:
    """Test that submit posts the survey result and parses the acknowledgement response.

    Verifies:
    - POST request is made to the correct endpoint
    - Request body contains correct survey data
    - Acknowledgement response is correctly parsed
    - Result ID is extracted from the response
    """
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        """Mock handler that captures the request and returns a success response.

        Args:
            request: The incoming HTTP request.

        Returns:
            httpx.Response: A 200 OK response with a result acknowledgement.
        """
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            HTTPStatus.OK,
            json={"message": "Result stored successfully", "result_id": "result-123"},
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))
    acknowledgement = client.submit(_build_result())

    assert acknowledgement.result_id == "result-123"
    assert captured_request is not None
    assert captured_request.method == "POST"
    assert str(captured_request.url) == ("https://gateway.example/v1/survey-assist/result")
    body = json.loads(captured_request.content)
    assert body["responses"][0]["survey_assist_interactions"] == []
    assert body["survey_id"] == "test_survey"
    assert body["wave_id"] == "test-wave"


def test_submit_does_not_retry_after_timeout() -> None:
    """Test that submit does not retry on read timeout errors.

    Verifies:
    - Timeout errors are caught and wrapped in ResultSubmissionTimeoutError
    - No retry attempts are made
    - Only one request is issued
    """
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        """Mock handler that raises a read timeout error.

        Args:
            request: The incoming HTTP request.

        Raises:
            httpx.ReadTimeout: Always raises a read timeout error.
        """
        nonlocal request_count
        request_count += 1
        raise httpx.ReadTimeout("Request timed out", request=request)

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(ResultSubmissionTimeoutError):
        client.submit(_build_result())

    assert request_count == 1


def test_submit_does_not_retry_after_gateway_timeout() -> None:
    """Test that submit does not retry on HTTP 504 Gateway Timeout responses.

    Verifies:
    - 504 Gateway Timeout responses are treated as errors
    - No retry attempts are made
    - Only one request is issued
    """
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        """Mock handler that returns a 504 Gateway Timeout response.

        Args:
            request: The incoming HTTP request.

        Returns:
            httpx.Response: A 504 Gateway Timeout response.
        """
        nonlocal request_count
        request_count += 1
        return httpx.Response(HTTPStatus.GATEWAY_TIMEOUT, request=request)

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(ResultSubmissionError):
        client.submit(_build_result())

    assert request_count == 1


def test_submit_raises_error_for_invalid_acknowledgement() -> None:
    """Test that submit raises an error when the acknowledgement response is not valid JSON.

    Verifies:
    - Invalid JSON responses are detected
    - ResultSubmissionError is raised for malformed responses
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Mock handler that returns invalid JSON.

        Args:
            request: The incoming HTTP request.

        Returns:
            httpx.Response: A 200 OK response with non-JSON content.
        """
        return httpx.Response(
            HTTPStatus.OK,
            content=b"not-json",
            request=request,
        )

    client = _create_client(httpx.MockTransport(handler))

    with pytest.raises(ResultSubmissionError):
        client.submit(_build_result())
