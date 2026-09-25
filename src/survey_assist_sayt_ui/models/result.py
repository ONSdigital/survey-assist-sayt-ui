"""Models for Survey Assist API result requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InputField(BaseModel):
    """Represents a single input field for a Survey Assist interaction.

    Attributes:
        field: The name or identifier of the input field.
        value: The value provided for the input field.
    """

    field: str
    value: str


class FollowUpQuestion(BaseModel):
    """Represents a single follow-up question in a Survey Assist interaction.

    Attributes:
        id: Unique identifier for the follow-up question.
        text: The question text to display to the user.
        type: The input type of the question (text, textarea, or select).
        select_options: List of options for select-type questions. None for other types.
        response: The user's response to the follow-up question.
    """

    id: str
    text: str
    type: Literal["text", "textarea", "select"]
    select_options: list[str] | None = None
    response: str


class FollowUp(BaseModel):
    """Container for follow-up questions in a Survey Assist interaction.

    Attributes:
        questions: List of follow-up questions to present to the user.
    """

    questions: list[FollowUpQuestion]


class Candidate(BaseModel):
    """Represents a candidate classification or lookup result.

    Attributes:
        code: The classification code or business/occupational code.
        description: Human-readable description of the code.
        likelihood: Confidence score (0-1) indicating the likelihood
                    of this being the correct classification.
    """

    code: str
    description: str
    likelihood: float


class ClassificationResponse(BaseModel):
    """Response from a classification request to Survey Assist API.

    Attributes:
        classified: Whether a classification was successfully determined.
        code: The primary classification code, if classified is True.
        description: Description of the primary classification code.
        reasoning: Explanation of the classification reasoning.
        candidates: List of candidate classifications with their likelihoods.
        follow_up: Follow-up questions to refine or confirm the classification.
    """

    classified: bool
    code: str | None = None
    description: str | None = None
    reasoning: str
    candidates: list[Candidate]
    follow_up: FollowUp


class PotentialDivision(BaseModel):
    """Represents a potential division in a lookup response.

    Attributes:
        code: The division code.
        title: The title or name of the division.
        detail: Optional additional details about the division.
    """

    code: str
    title: str
    detail: str | None = None


class PotentialCode(BaseModel):
    """Represents a potential code in a lookup response.

    Attributes:
        code: The classification or business/occupational code.
        description: Human-readable description of the code.
    """

    code: str
    description: str


class LookupResponse(BaseModel):
    """Response from a lookup request to Survey Assist API.

    Attributes:
        found: Whether an exact match was found for the lookup query.
        code: The exact matching code, if found is True.
        code_division: The division of the matching code.
        potential_codes_count: Total count of potential matching codes.
        potential_divisions: List of potential division matches.
        potential_codes: List of potential code matches.
    """

    found: bool
    code: str | None = None
    code_division: str | None = None
    potential_codes_count: int
    potential_divisions: list[PotentialDivision]
    potential_codes: list[PotentialCode]


class SurveyAssistInteraction(BaseModel):
    """Represents a single interaction with Survey Assist during a survey response.

    Attributes:
        type: The type of interaction (classify or lookup).
        flavour: The classification system used (sic for business activity or soc for occupation).
        time_start: Timestamp when the interaction began.
        time_end: Timestamp when the interaction completed.
        input: List of input fields provided by the user for this interaction.
        response: The response from Survey Assist (classification or lookup).
    """

    type: Literal["classify", "lookup"]
    flavour: Literal["sic", "soc"]
    time_start: datetime
    time_end: datetime
    input: list[InputField]
    response: ClassificationResponse | LookupResponse


class Response(BaseModel):
    """Represents a single person's response to a survey, including Survey Assist interactions.

    Attributes:
        person_id: Unique identifier for the respondent.
        time_start: Timestamp when the respondent started the survey.
        time_end: Timestamp when the respondent completed the survey.
        survey_assist_interactions: List of Survey Assist interactions during the survey response.
    """

    person_id: str
    time_start: datetime
    time_end: datetime
    survey_assist_interactions: list[SurveyAssistInteraction]


class SurveyAssistResult(BaseModel):
    """Represents the complete result set for a survey with Survey Assist interactions.

    Attributes:
        survey_id: Unique identifier for the survey.
        wave_id: Wave identifier for the survey collection.
        case_id: Case identifier for this survey instance.
        user: Identifier for the user/respondent.
        time_start: Timestamp when the survey session started.
        time_end: Timestamp when the survey session completed.
        responses: List of responses from all respondents involved in this survey.
    """

    survey_id: str
    wave_id: str
    case_id: str
    user: str
    time_start: datetime
    time_end: datetime
    responses: list[Response]


class ResultResponse(BaseModel):
    """Response from submitting survey results to the API.

    Attributes:
        message: Status message indicating success or failure of the submission.
        result_id: Unique identifier for the submitted result, if submission was successful.
    """

    message: str
    result_id: str | None = None
