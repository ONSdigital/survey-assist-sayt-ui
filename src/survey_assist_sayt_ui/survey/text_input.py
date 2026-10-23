"""Clean free-text answers before they are saved or searched.

Character patterns are copied from the public-test UI SafeInputFilter.
"""

import re

_SMART_QUOTE_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]")
_REMOVED_CHARACTERS = re.compile(r"[^A-Za-z\u00C0-\u00FF0-9\s.,!?;:'\"()\-\u2013\u2014£€%&]")
_REPEATED_CHARACTER = re.compile(r"(.)\1{3,}")


def clean_saved_answer(value: str) -> str:
    """Return text that can be stored for a free-text answer.

    Letters, including accented letters, digits, spaces, and
    ``.,!?;:'"()-–—£€%&`` are kept. An ampersand is kept. Other characters
    are removed.
    """
    text = re.sub(r"\s+", " ", value)
    text = _REPEATED_CHARACTER.sub(r"\1", text)
    text = text.translate(_SMART_QUOTE_MAP)
    text = _CONTROL_CHARACTERS.sub("", text)
    text = _REMOVED_CHARACTERS.sub("", text)
    return text.strip()


def suggestion_search_text(value: str) -> str:
    """Return the query sent to the suggestion search.

    The saved answer keeps an ampersand. The search does not.
    """
    return clean_saved_answer(value).replace("&", "")
