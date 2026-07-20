"""Tests for loading JSON survey definitions."""

from pathlib import Path

import pytest

from survey_assist_sayt_ui.survey.loader import (
    SurveyDefinitionInvalidError,
    SurveyDefinitionNotFoundError,
    load_survey_definition,
)


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
