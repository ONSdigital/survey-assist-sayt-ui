"""Client for submitting survey feedback via the Survey Assist API."""

from __future__ import annotations

import logging
from typing import Protocol

from pydantic import ValidationError

from survey_assist_sayt_ui.models.feedback import FeedbackResponse, FeedbackResult
from survey_assist_sayt_ui.services.survey_assist_api import (
    SurveyAssistApiClient,
    SurveyAssistApiError,
    SurveyAssistApiTimeoutError,
)

logger = logging.getLogger(__name__)


class FeedbackSubmissionError(RuntimeError):
    """Raised when survey feedback cannot be submitted."""


class FeedbackSubmissionTimeoutError(FeedbackSubmissionError):
    """Raised when survey feedback submission times out."""


class SurveyFeedbackSubmissionClient(Protocol):  # pylint: disable=too-few-public-methods
    """Interface for survey feedback submission implementations."""

    def submit(self, feedback: FeedbackResult) -> FeedbackResponse:
        """Submit survey feedback."""


FEEDBACK_ENDPOINT = "feedback"


class HttpSurveyFeedbackSubmissionClient:  # pylint: disable=too-few-public-methods
    """Submit feedback using the shared Survey Assist API client."""

    def __init__(self, api_client: SurveyAssistApiClient) -> None:
        self._api_client = api_client

    def submit(self, feedback: FeedbackResult) -> FeedbackResponse:
        """POST feedback once and validate the API acknowledgement."""
        try:
            response = self._api_client.post(
                FEEDBACK_ENDPOINT,
                body=feedback.model_dump(mode="json"),
                retry_on_timeout=False,
            )
            acknowledgement = FeedbackResponse.model_validate(response.json())
        except SurveyAssistApiTimeoutError as error:
            logger.warning("Survey Assist feedback submission timed out")
            raise FeedbackSubmissionTimeoutError(
                "Survey Assist feedback submission timed out"
            ) from error
        except (SurveyAssistApiError, ValidationError, ValueError) as error:
            logger.error(
                "Survey Assist feedback submission failed error_type=%s",
                type(error).__name__,
            )
            raise FeedbackSubmissionError(
                "Survey Assist feedback submission failed"
            ) from error

        if acknowledgement.feedback_id:
            logger.info("Survey Assist feedback accepted feedback_id_present=true")
        else:
            logger.warning(
                "Survey Assist feedback response did not include a feedback_id"
            )

        return acknowledgement
