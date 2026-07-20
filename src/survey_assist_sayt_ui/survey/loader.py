"""Load and validate JSON survey definitions."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import cast
from urllib.parse import urlparse

from survey_assist_sayt_ui.survey.models import SurveyDefinition

SECTION_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_BLOCK_TYPES = {"paragraph", "button", "panel"}
SUPPORTED_INLINE_TYPES = {"text", "link"}
SUPPORTED_PANEL_VARIANTS = {"info", "warn", "warn-branded", "pending"}


class SurveyDefinitionError(ValueError):
    """Base exception for invalid survey definitions."""


class SurveyDefinitionNotFoundError(SurveyDefinitionError):
    """Raised when the configured survey definition cannot be found."""


class SurveyDefinitionInvalidError(SurveyDefinitionError):
    """Raised when a survey definition is malformed or unsupported."""


def load_survey_definition(path: Path) -> SurveyDefinition:
    """Load and validate a survey definition from a JSON file.

    Args:
        path: Path to the JSON survey definition.

    Returns:
        SurveyDefinition: Validated survey definition.

    Raises:
        SurveyDefinitionNotFoundError: If the configured file does not exist.
        SurveyDefinitionInvalidError: If the JSON or survey structure is invalid.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SurveyDefinitionNotFoundError(f"Survey definition was not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SurveyDefinitionInvalidError(
            f"Survey definition contains invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {path}"
        ) from exc
    except OSError as exc:
        raise SurveyDefinitionError(f"Survey definition could not be read: {path}") from exc

    if not isinstance(payload, dict):
        raise SurveyDefinitionInvalidError(
            "Survey definition must contain a JSON object at its root"
        )

    _validate_survey_definition(payload)

    return cast(SurveyDefinition, payload)


def _validate_survey_definition(payload: dict[str, object]) -> None:
    """Validate the supported survey definition structure.

    Args:
        payload: Parsed JSON survey definition.

    Raises:
        SurveyDefinitionInvalidError: If a required field is invalid.
    """
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise SurveyDefinitionInvalidError(f"Unsupported survey schema version: {schema_version!r}")

    _require_non_empty_string(payload, "survey_title")
    _require_non_empty_string(payload, "wave_id")

    survey_intro = _require_mapping(payload, "survey_intro")
    enabled = survey_intro.get("enabled")

    if not isinstance(enabled, bool):
        raise SurveyDefinitionInvalidError("survey_intro.enabled must be a boolean")

    intro = survey_intro.get("intro")

    if not enabled:
        return

    if not isinstance(intro, dict):
        raise SurveyDefinitionInvalidError(
            "survey_intro.intro is required when survey_intro.enabled is true"
        )

    navigation = _require_mapping(intro, "navigation")
    sections = _require_list(intro, "sections")

    _require_non_empty_string(navigation, "header")
    _require_non_empty_string(navigation, "aria_label")

    section_ids = _validate_sections(sections)
    _validate_navigation(navigation, section_ids)


def _validate_sections(sections: list[object]) -> set[str]:
    """Validate survey introduction sections.

    Args:
        sections: Raw section definitions.

    Returns:
        set[str]: Validated unique section identifiers.

    Raises:
        SurveyDefinitionInvalidError: If section content is invalid.
    """
    section_ids: set[str] = set()

    if not sections:
        raise SurveyDefinitionInvalidError("survey_intro.intro.sections must not be empty")

    for index, section_value in enumerate(sections):
        if not isinstance(section_value, dict):
            raise SurveyDefinitionInvalidError(f"Section {index} must be an object")

        section = cast(dict[str, object], section_value)
        section_id = _require_non_empty_string(section, "id")
        _require_non_empty_string(section, "heading")

        if not SECTION_ID_PATTERN.fullmatch(section_id):
            raise SurveyDefinitionInvalidError(f"Invalid section id: {section_id!r}")

        if section_id in section_ids:
            raise SurveyDefinitionInvalidError(f"Duplicate section id: {section_id!r}")

        section_ids.add(section_id)

        blocks = _require_list(section, "blocks")
        for block_index, block in enumerate(blocks):
            _validate_block(block, section_id, block_index)

    return section_ids


def _validate_block(
    value: object,
    section_id: str,
    block_index: int,
) -> None:
    """Validate one survey content block.

    Args:
        value: Raw JSON block value.
        section_id: Identifier of the containing section.
        block_index: Position of the block within the section.

    Raises:
        SurveyDefinitionInvalidError: If the block is invalid.
    """
    if not isinstance(value, dict):
        raise SurveyDefinitionInvalidError(
            f"Block {block_index} in section {section_id!r} must be an object"
        )

    block = cast(dict[str, object], value)
    block_type = block.get("type")

    if block_type not in SUPPORTED_BLOCK_TYPES:
        raise SurveyDefinitionInvalidError(
            f"Unsupported block type {block_type!r} in section {section_id!r}"
        )

    if block_type == "paragraph":
        _validate_inline_content(_require_list(block, "content"))
        return

    if block_type == "button":
        _require_non_empty_string(block, "text")
        _validate_link(_require_non_empty_string(block, "link"))
        return

    variant = _require_non_empty_string(block, "variant")
    if variant not in SUPPORTED_PANEL_VARIANTS:
        raise SurveyDefinitionInvalidError(f"Unsupported panel variant: {variant!r}")

    _require_non_empty_string(block, "heading")

    for paragraph in _require_list(block, "paragraphs"):
        if not isinstance(paragraph, list):
            raise SurveyDefinitionInvalidError("Panel paragraphs must be arrays of inline content")
        _validate_inline_content(paragraph)


def _validate_link(link: str) -> None:
    """Validate a configured link.

    Args:
        link: Configured internal, anchor, email or HTTPS link.

    Raises:
        SurveyDefinitionInvalidError: If the link protocol or structure is
            unsupported.
    """
    if link.startswith("#"):
        return

    if link.startswith("/") and not link.startswith("//"):
        return

    parsed = urlparse(link)

    if parsed.scheme == "https" and parsed.netloc:
        return

    if parsed.scheme == "mailto" and parsed.path:
        return

    raise SurveyDefinitionInvalidError(f"Unsupported link in {link!r}")


def _validate_navigation(
    navigation: dict[str, object],
    section_ids: set[str],
) -> None:
    """Validate introduction navigation entries.

    Args:
        navigation: Navigation configuration.
        section_ids: Valid section identifiers.

    Raises:
        SurveyDefinitionInvalidError: If a navigation entry is invalid.
    """
    entries = _require_list(navigation, "entries")

    for entry_value in entries:
        if not isinstance(entry_value, dict):
            raise SurveyDefinitionInvalidError("Navigation entries must be objects")

        entry = cast(dict[str, object], entry_value)
        link = _require_non_empty_string(entry, "link")
        _require_non_empty_string(entry, "text")

        if not link.startswith("#"):
            raise SurveyDefinitionInvalidError(
                f"Introduction navigation link must be an anchor: {link!r}"
            )

        if link.removeprefix("#") not in section_ids:
            raise SurveyDefinitionInvalidError(
                f"Navigation link does not match a section: {link!r}"
            )


def _require_non_empty_string(
    payload: dict[str, object],
    field_name: str,
) -> str:
    """Return a required non-empty string field.

    Args:
        payload: JSON object containing the field.
        field_name: Name of the required field.

    Returns:
        str: Validated string value.

    Raises:
        SurveyDefinitionInvalidError: If the field is missing, is not a string
            or contains only whitespace.
    """
    value = payload.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise SurveyDefinitionInvalidError(f"{field_name} must be a non-empty string")

    return value


def _require_mapping(
    payload: dict[str, object],
    field_name: str,
) -> dict[str, object]:
    """Return a required JSON object field.

    Args:
        payload: JSON object containing the field.
        field_name: Name of the required field.

    Returns:
        dict[str, object]: Validated JSON object.

    Raises:
        SurveyDefinitionInvalidError: If the field is missing or is not an
            object.
    """
    value = payload.get(field_name)

    if not isinstance(value, dict):
        raise SurveyDefinitionInvalidError(f"{field_name} must be an object")

    return cast(dict[str, object], value)


def _require_list(
    payload: dict[str, object],
    field_name: str,
) -> list[object]:
    """Return a required JSON array field.

    Args:
        payload: JSON object containing the field.
        field_name: Name of the required field.

    Returns:
        list[object]: Validated JSON array.

    Raises:
        SurveyDefinitionInvalidError: If the field is missing or is not an
            array.
    """
    value = payload.get(field_name)

    if not isinstance(value, list):
        raise SurveyDefinitionInvalidError(f"{field_name} must be an array")

    return value


def _validate_inline_content(items: list[object]) -> None:
    """Validate inline paragraph content.

    Inline content may contain plain text or links. Link entries must include
    valid link text and a supported URL.

    Args:
        items: Raw inline content definitions.

    Raises:
        SurveyDefinitionInvalidError: If inline content is empty or malformed.
    """
    if not items:
        raise SurveyDefinitionInvalidError("Inline content must not be empty")

    for index, item_value in enumerate(items):
        if not isinstance(item_value, dict):
            raise SurveyDefinitionInvalidError(f"Inline content item {index} must be an object")

        item = cast(dict[str, object], item_value)
        item_type = item.get("type")

        if item_type not in SUPPORTED_INLINE_TYPES:
            raise SurveyDefinitionInvalidError(
                f"Unsupported inline content type {item_type!r} " f"at position {index}"
            )

        _require_non_empty_string(item, "text")

        if item_type == "text":
            continue

        link = _require_non_empty_string(item, "link")
        _validate_link(link)

        new_window = item.get("new_window")
        if new_window is not None and not isinstance(new_window, bool):
            raise SurveyDefinitionInvalidError(
                f"new_window must be a boolean for inline content item {index}"
            )
