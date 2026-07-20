"""Tests for loading JSON survey definitions."""

import json
from pathlib import Path
from typing import cast

import pytest

from survey_assist_sayt_ui.survey.loader import (
    SurveyDefinitionInvalidError,
    SurveyDefinitionNotFoundError,
    load_survey_definition,
)
from survey_assist_sayt_ui.survey.models import SurveyDefinition


def test_load_survey_definition_raises_when_file_is_missing(
    tmp_path: Path,
) -> None:
    """Test that a missing survey definition raises a clear error."""
    missing_path = tmp_path / "missing.json"

    with pytest.raises(
        SurveyDefinitionNotFoundError,
        match="Survey definition was not found",
    ):
        load_survey_definition(missing_path)


def test_load_survey_definition_raises_for_invalid_json(
    tmp_path: Path,
) -> None:
    """Test that malformed JSON raises a clear validation error."""
    survey_path = tmp_path / "survey.json"
    survey_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="contains invalid JSON",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_unknown_navigation_section(
    tmp_path: Path,
) -> None:
    """Test that navigation links must reference configured sections."""
    survey_path = tmp_path / "survey.json"
    survey_path.write_text(
        """
        {
          "schema_version": 1,
          "survey_title": "Test survey",
          "wave_id": "test-wave",
          "survey_intro": {
            "enabled": true,
            "intro": {
              "navigation": {
                "header": "Contents",
                "aria_label": "Page sections",
                "entries": [
                  {"link": "#missing", "text": "Missing"}
                ]
              },
              "sections": [
                {
                  "id": "intro",
                  "heading": "Introduction",
                  "blocks": []
                }
              ]
            }
          },
          "survey_pages": {
            "enabled": true,
            "start_page_id": "q0",
            "pages": [
              {
                "page_id": "q0",
                "page_type": "question",
                "page_title": "Test question",
                "question_name": "test_question",
                "question": {
                  "text": "Test question text"
                },
                "answer": {
                  "type": "text",
                  "name": "test-answer",
                  "required": true
                },
                "submit_button": {
                  "text": "Save and continue"
                }
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="does not match a section",
    ):
        load_survey_definition(survey_path)


def _write_survey_definition(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> Path:
    """Write a survey definition to a temporary JSON file.

    Args:
        tmp_path: Temporary directory supplied by pytest.
        survey_definition: Survey definition to serialise.

    Returns:
        Path: Path to the temporary survey definition.
    """
    survey_path = tmp_path / "survey.json"
    survey_path.write_text(
        json.dumps(survey_definition),
        encoding="utf-8",
    )
    return survey_path


def test_load_survey_definition_rejects_duplicate_page_ids(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that survey page identifiers must be unique."""
    pages = survey_definition["survey_pages"]["pages"]
    pages[1]["page_id"] = pages[0]["page_id"]

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="Duplicate survey page id",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_invalid_start_page_id(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that the start page must reference a configured page."""
    survey_definition["survey_pages"]["start_page_id"] = "missing"

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="start_page_id does not match a survey page",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_unsupported_answer_type(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that unsupported answer types are rejected."""
    pages = survey_definition["survey_pages"]["pages"]
    answer = cast(dict[str, object], pages[0]["answer"])
    answer["type"] = "checkbox"

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="Unsupported answer type",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_radio_without_options(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that radio questions require at least one option."""
    pages = survey_definition["survey_pages"]["pages"]
    answer = cast(dict[str, object], pages[0]["answer"])
    answer["options"] = []

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="Radio answers must define at least one option",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_duplicate_radio_values(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that radio option values must be unique."""
    pages = survey_definition["survey_pages"]["pages"]
    answer = cast(dict[str, object], pages[0]["answer"])
    options = cast(list[dict[str, object]], answer["options"])
    options[1]["value"] = options[0]["value"]

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="Duplicate radio option value",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_invalid_text_character_limit(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that text character limits must be positive integers."""
    pages = survey_definition["survey_pages"]["pages"]
    answer = cast(dict[str, object], pages[1]["answer"])
    answer["character_limit"] = 0

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="answer.character_limit must be a positive integer",
    ):
        load_survey_definition(survey_path)


def test_load_survey_definition_rejects_unknown_placeholder_source(
    tmp_path: Path,
    survey_definition: SurveyDefinition,
) -> None:
    """Test that placeholders must reference an earlier question."""
    question = survey_definition["survey_pages"]["pages"][1]["question"]
    question["text"] = "Your answer was PLACEHOLDER_TEXT"
    question["placeholders"] = [
        {
            "placeholder": "PLACEHOLDER_TEXT",
            "source_question_name": "missing_question",
        }
    ]

    survey_path = _write_survey_definition(
        tmp_path,
        survey_definition,
    )

    with pytest.raises(
        SurveyDefinitionInvalidError,
        match="must reference an earlier question_name",
    ):
        load_survey_definition(survey_path)
