"""Type definitions for JSON-configured surveys. TypeDict is compatible with Jinja"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class InlineContent(TypedDict):
    """Inline text or link content."""

    type: Literal["text", "link"]
    text: str
    link: NotRequired[str]
    new_window: NotRequired[bool]


class ParagraphBlock(TypedDict):
    """Paragraph content block."""

    type: Literal["paragraph"]
    content: list[InlineContent]


class ButtonBlock(TypedDict):
    """ONS button content block."""

    type: Literal["button"]
    text: str
    link: NotRequired[str]
    target_page_id: NotRequired[str]
    variants: NotRequired[list[str]]


class PanelBlock(TypedDict):
    """ONS information panel content block."""

    type: Literal["panel"]
    variant: str
    heading: str
    paragraphs: list[list[InlineContent]]


ContentBlock = ParagraphBlock | ButtonBlock | PanelBlock


class SurveySection(TypedDict):
    """A section displayed on a survey introduction page."""

    id: str
    heading: str
    blocks: list[ContentBlock]


class NavigationEntry(TypedDict):
    """A link to a section within the introduction page."""

    link: str
    text: str


class SurveyNavigation(TypedDict):
    """Introduction page table-of-contents configuration."""

    header: str
    aria_label: str
    entries: list[NavigationEntry]


class SurveyIntroContent(TypedDict):
    """Content displayed on the survey introduction page."""

    navigation: SurveyNavigation
    sections: list[SurveySection]


class SurveyIntro(TypedDict):
    """Survey introduction feature configuration."""

    enabled: bool
    intro: NotRequired[SurveyIntroContent]


class SurveyDefinition(TypedDict):
    """Complete versioned survey definition."""

    schema_version: int
    survey_title: str
    wave_id: str
    survey_intro: SurveyIntro
    survey_pages: SurveyPages


class RadioOption(TypedDict):
    """Option displayed by an ONS radio component."""

    id: str
    label: str
    value: str


class RadioAnswer(TypedDict):
    """Radio answer configuration."""

    type: Literal["radio"]
    name: str
    required: bool
    options: list[RadioOption]


class TextAnswer(TypedDict):
    """Text answer configuration."""

    type: Literal["text"]
    name: str
    required: bool
    multiline: NotRequired[bool]
    rows: NotRequired[int]
    character_limit: NotRequired[int]
    placeholder: NotRequired[str]


QuestionAnswer = RadioAnswer | TextAnswer


class QuestionGuidance(TypedDict):
    """Optional question guidance."""

    content: str


class QuestionJustification(TypedDict):
    """Optional explanation of why a question is asked."""

    title: str
    content: str


class QuestionPlaceholder(TypedDict):
    """Replacement value used within configurable question text."""

    placeholder: str
    source_question_name: str


class QuestionContent(TypedDict):
    """Content displayed by the ONS question component."""

    text: str
    description: NotRequired[str]
    guidance: NotRequired[QuestionGuidance]
    justification: NotRequired[QuestionJustification]
    placeholders: NotRequired[list[QuestionPlaceholder]]


class SubmitButton(TypedDict):
    """Question submit button configuration."""

    text: str


class QuestionPage(TypedDict):
    """A configurable survey question page."""

    page_id: str
    page_type: Literal["question"]
    page_title: str
    question_name: str
    question: QuestionContent
    answer: QuestionAnswer
    submit_button: SubmitButton


class SurveyPages(TypedDict):
    """Ordered pages making up the survey journey."""

    enabled: bool
    start_page_id: str
    pages: list[QuestionPage]


class SurveyResponse(TypedDict):
    """Response stored for one survey question."""

    question_name: str
    response_name: str
    value: str


SurveyResponses = dict[str, SurveyResponse]
