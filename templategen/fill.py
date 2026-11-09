"""Send time: fill an approved template with customer values. No LLM involved.

Two functions:
  fill()                  - deterministic placeholder replacement
  check_customer_value()  - a light sanity check on values before they go into a letter
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .catalog import PLACEHOLDERS

# Anything in square brackets on one line, e.g. [CUSTOMER_NAME], [Your Name], [DATE].
BRACKETED = re.compile(r"\[[^\[\]\n]{1,40}\]")


def find_placeholders(text: str) -> list[str]:
    """Every bracketed placeholder in the text, in order of appearance (repeats included)."""
    return BRACKETED.findall(text)


@dataclass
class FillResult:
    letter: str
    replacements: dict[str, int]  # placeholder -> how many times it was replaced
    leftovers: list[str] = field(default_factory=list)  # bracketed text still in the letter


def fill(template: str, values: dict[str, str]) -> FillResult:
    """Replace each placeholder with its value, in a single pass.

    A single pass matters: if a customer's name itself contains "[TOUR_GUIDE]", it is inserted
    as-is and never replaced again. Chained str.replace() calls (as in the notebook) would
    replace it on the second call.
    """
    wanted = {p: values[p] for p in PLACEHOLDERS if p in values}
    counts = {p: 0 for p in wanted}
    if not wanted:
        return FillResult(template, counts, find_placeholders(template))

    pattern = re.compile("|".join(re.escape(p) for p in wanted))

    def swap(match: re.Match) -> str:
        counts[match.group(0)] += 1
        return wanted[match.group(0)]

    # Find leftovers in the template (not the letter), so customer text is never mistaken for one.
    leftovers = [p for p in find_placeholders(template) if p not in wanted]
    return FillResult(pattern.sub(swap, template), counts, leftovers)


# Letters (any alphabet), spaces, hyphens, apostrophes and periods, as in "Anne-Marie O'Neil Jr."
NAME_CHARS = re.compile(r"^[^\W\d_]+(?:[ \-'.]+[^\W\d_]*)*$")
MAX_NAME_LENGTH = 60
MAX_NAME_WORDS = 5


def check_customer_value(value: str) -> list[str]:
    """Warnings about a value that doesn't look like a person's name. Empty list = looks fine.

    This is a separate defense layer. The template already guarantees the value can't change
    what the letter promises; this check catches values that would make the letter look wrong.
    """
    warnings = []
    stripped = value.strip()
    if not stripped:
        return ["The value is empty."]
    if len(stripped) > MAX_NAME_LENGTH:
        warnings.append(f"Longer than {MAX_NAME_LENGTH} characters ({len(stripped)}).")
    if len(stripped.split()) > MAX_NAME_WORDS:
        warnings.append(
            f"Has {len(stripped.split())} words; names rarely have more than {MAX_NAME_WORDS}. "
            "It may be a sentence."
        )
    if "\n" in value:
        warnings.append("Contains a line break.")
    if "[" in value or "]" in value:
        warnings.append("Contains square brackets, which could look like a placeholder.")
    if not NAME_CHARS.match(stripped.replace("\n", " ")):
        warnings.append(
            "Contains characters other than letters, spaces, hyphens, apostrophes and periods."
        )
    return warnings
