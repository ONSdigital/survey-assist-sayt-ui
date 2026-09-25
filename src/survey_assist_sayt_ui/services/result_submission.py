"""Client for submitting survey results via the Survey Assist API."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from survey_assist_sayt_ui.models.result import ResultResponse, SurveyAssistResult
from survey_assist_sayt_ui.services.survey_assist_api import (
    SurveyAssistApiClient,
    SurveyAssistApiError,
    SurveyAssistApiTimeoutError,
)

logger = logging.getLogger(__name__)


class ResultSubmissionError(RuntimeError):
    """Raised when a survey result cannot be submitted."""


class ResultSubmissionTimeoutError(ResultSubmissionError):
    """Raised when survey result submission times out."""


class HttpSurveyResultSubmissionClient:  # pylint: disable=too-few-public-methods
    """Submit a result using the shared Survey Assist API client."""

    def __init__(self, api_client: SurveyAssistApiClient) -> None:
        self._api_client = api_client

    def submit(self, result: SurveyAssistResult) -> ResultResponse:
        """POST a result once and validate the API acknowledgement."""
        try:
            response = self._api_client.post(
                "result",
                body=result.model_dump(mode="json"),
                retry_on_timeout=False,
            )
            acknowledgement = ResultResponse.model_validate(response.json())
        except SurveyAssistApiTimeoutError as error:
            logger.warning("Survey Assist result submission timed out")
            raise ResultSubmissionTimeoutError(
                "Survey Assist result submission timed out"
            ) from error
        except (SurveyAssistApiError, ValidationError, ValueError) as error:
            logger.error(
                "Survey Assist result submission failed error_type=%s",
                type(error).__name__,
            )
            raise ResultSubmissionError("Survey Assist result submission failed") from error

        if acknowledgement.result_id:
            logger.info(
                "Survey Assist result accepted result_id_present=true %s", acknowledgement.result_id
            )
        else:
            logger.warning("Survey Assist result response did not include a result_id")

        return acknowledgement
