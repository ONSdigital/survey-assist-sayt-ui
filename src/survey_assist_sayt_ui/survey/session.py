"""Utilities for managing survey session data."""

from __future__ import annotations

from flask import session

SURVEY_RESPONSES_KEY = "survey_responses"

SURVEY_SESSION_KEYS = frozenset(
    {
        SURVEY_RESPONSES_KEY,
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
