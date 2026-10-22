"""Models for Survey Assist API feedback requests and responses."""

from pydantic import BaseModel


class FeedbackQuestion(BaseModel):
    """One feedback answer sent to the Survey Assist API."""

    response: str
    response_name: str
    response_options: list[str] | None


class FeedbackResult(BaseModel):
    """Feedback saved separately from the survey result."""

    case_id: str
    person_id: str
    survey_id: str
    wave_id: str
    questions: list[FeedbackQuestion]


class FeedbackResponse(BaseModel):
    """Acknowledgement from the feedback endpoint."""

    message: str
    feedback_id: str | None = None
