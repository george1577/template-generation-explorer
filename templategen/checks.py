"""Automatic checks: rules that flag likely problems in a template for the reviewer.

They never approve or reject anything. A template with no findings still needs a person to
approve it, and a person may approve a template with findings (e.g. a correct opening time).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import PLACEHOLDERS
from .fill import find_placeholders

# Severity: "error" means the template can't be filled correctly as it stands;
# "verify" means a person must check a fact before approving.
ERROR = "error"
VERIFY = "verify"


@dataclass(frozen=True)
class Finding:
    check: str  # which check produced it
    severity: str  # ERROR or VERIFY
    message: str
    snippet: str = ""  # the text that triggered it, if any


# ---------------------------------------------------------------- (a) missing placeholders


def check_missing_placeholders(text: str) -> list[Finding]:
    found = set(find_placeholders(text))
    return [
        Finding(
            "missing placeholder",
            ERROR,
            f"{p} never appears, so that detail can't be filled in.",
            p,
        )
        for p in PLACEHOLDERS
        if p not in found
    ]


# ---------------------------------------------------------------- (b) unknown placeholders


def check_unknown_placeholders(text: str) -> list[Finding]:
    unknown = []
    for p in find_placeholders(text):
        if p not in PLACEHOLDERS and p not in unknown:
            unknown.append(p)
    return [
        Finding(
            "unknown placeholder",
            ERROR,
            f"{p} is not one we know how to fill; it would reach the customer as-is.",
            p,
        )
        for p in unknown
    ]


# ---------------------------------------------------------------- (c) wrong language

POLISH_LETTERS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
ENGLISH_WORDS = {
    "the", "and", "you", "your", "to", "of", "is", "will", "we", "with", "for", "this",
    "are", "be", "in", "can", "see", "our", "it", "that",
}
# Words that are also English (or English-looking), like "i", "w", "to", "do", are left out:
# "I'm" would otherwise count as the Polish word "i".
POLISH_WORDS = {
    "na", "się", "nie", "jest", "że", "jak", "dla", "oraz", "będzie", "który", "która",
    "nas", "pan", "pani", "bardzo", "państwa", "czy", "ale", "już", "tym", "jestem",
}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def guess_language(text: str) -> tuple[str, dict[str, float]]:
    """Guess "English" or "Polish" by counting common words and Polish-only letters.

    Returns the guess and the scores behind it, so the app can show its working.
    Placeholders are removed first, since [CUSTOMER_NAME] is English in every template.
    """
    body = re.sub(r"\[[^\[\]\n]{1,40}\]", " ", text)
    words = [w.lower() for w in WORD.findall(body)]
    if not words:
        return "unknown", {"English": 0.0, "Polish": 0.0}
    english = sum(w in ENGLISH_WORDS for w in words) / len(words)
    polish_letters = sum(ch in POLISH_LETTERS for ch in body) / max(len(body), 1)
    # Each Polish-only letter is strong evidence, so weight it up (x10).
    polish = sum(w in POLISH_WORDS for w in words) / len(words) + 10 * polish_letters
    scores = {"English": round(english, 3), "Polish": round(polish, 3)}
    return ("English" if english >= polish else "Polish"), scores


def check_language(text: str, expected: str) -> list[Finding]:
    guess, scores = guess_language(text)
    if guess == expected or guess == "unknown":
        return []
    return [
        Finding(
            "wrong language",
            ERROR,
            f"Asked for {expected}, but this reads like {guess} "
            f"(English score {scores['English']}, Polish score {scores['Polish']}).",
        )
    ]


# ---------------------------------------------------------------- (d) facts to verify

MONTHS = (
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|"
    r"listopada|grudnia"
)
FACT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("price", re.compile(r"[€$£]\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|EUR|euros?|USD|dollars?|zł|PLN)\b", re.I)),
    ("time", re.compile(r"\b\d{1,2}[:.]\d{2}\s?(?:am|pm|a\.m\.|p\.m\.)?|\b\d{1,2}\s?(?:am|pm|a\.m\.|p\.m\.)", re.I)),
    ("date", re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s(?:{MONTHS})\b|\b(?:{MONTHS})\s\d{{1,2}}\b|\b\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?\b", re.I)),
    ("phone number", re.compile(r"\+?\d[\d \-]{7,}\d")),
    ("web or email address", re.compile(r"https?://\S+|www\.\S+|\b[\w.+-]+@[\w-]+\.[\w.]+\b", re.I)),
]


def check_facts_to_verify(text: str) -> list[Finding]:
    """Rules run in the order of FACT_PATTERNS. Text already flagged by an earlier rule is
    skipped by later ones, so "€25.50" is reported once as a price, not again as the time "25.50".
    """
    findings = []
    taken: list[tuple[int, int]] = []
    for kind, pattern in FACT_PATTERNS:
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue
            taken.append(match.span())
            findings.append(
                Finding(
                    "fact to verify",
                    VERIFY,
                    f"Mentions a {kind}. The model may have made it up; check it's correct.",
                    match.group(0).strip(),
                )
            )
    return findings


# ---------------------------------------------------------------- all together


def run_checks(text: str, expected_language: str) -> list[Finding]:
    """Run all four automatic checks. Errors first, then facts to verify."""
    return (
        check_missing_placeholders(text)
        + check_unknown_placeholders(text)
        + check_language(text, expected_language)
        + check_facts_to_verify(text)
    )
