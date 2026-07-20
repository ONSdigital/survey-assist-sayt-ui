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
    link: str
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
