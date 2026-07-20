"""Tests for survey session utilities."""

from flask import Flask, session

from survey_assist_sayt_ui.survey.session import (
    SURVEY_RESPONSES_KEY,
    clear_survey_session_data,
)


def test_clear_survey_session_data_removes_survey_values(
    app: Flask,
) -> None:
    """Test that survey-specific session values are removed."""
    with app.test_request_context():
        session[SURVEY_RESPONSES_KEY] = {
            "q0": {
                "value": "16-24",
            }
        }
        session["unrelated-key"] = "keep-me"

        removed_keys = clear_survey_session_data()

        assert removed_keys == {SURVEY_RESPONSES_KEY}
        assert SURVEY_RESPONSES_KEY not in session
        assert session["unrelated-key"] == "keep-me"


def test_clear_survey_session_data_handles_missing_values(
    app: Flask,
) -> None:
    """Test that clearing an empty survey session is safe."""
    with app.test_request_context():
        removed_keys = clear_survey_session_data()

        assert removed_keys == set()
