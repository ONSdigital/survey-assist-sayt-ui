"""Utilities for managing survey session data."""

from __future__ import annotations

from flask import session

SURVEY_RESPONSES_KEY = "survey_responses"
SURVEY_FEEDBACK_RESPONSES_KEY = "survey_feedback_responses"
SURVEY_RESPONSE_START_TIME_KEY = "survey_response_start_time"
SUGGESTION_TIME_START_KEY = "suggestion_time_start"
SUGGESTION_TIME_END_KEY = "suggestion_time_end"
QUESTION_RENDER_TIME_KEY = "question_render_time"
QUESTION_RENDER_PAGE_ID_KEY = "question_render_page_id"

SURVEY_SESSION_KEYS = frozenset(
    {
        SURVEY_RESPONSES_KEY,
        SURVEY_FEEDBACK_RESPONSES_KEY,
        SURVEY_RESPONSE_START_TIME_KEY,
        SUGGESTION_TIME_START_KEY,
        SUGGESTION_TIME_END_KEY,
        QUESTION_RENDER_TIME_KEY,
        QUESTION_RENDER_PAGE_ID_KEY,
    }
)


def clear_survey_session_data() -> set[str]:
    """Remove all survey-specific values from the current session.

    Returns:
        set[str]: Session keys that were removed.
    """
    removed_keys: set[str] = set()

    for key in SURVEY_SESSION_KEYS:
        if key in session:
            session.pop(key)
            removed_keys.add(key)

    return removed_keys
