"""What the tour company sells: the attributes that make up a template key.

Values are copied from the reference notebook (examples/29_template_generation).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

DESTINATIONS = ["Toledo, Spain", "Avila & Segovia", "Escorial Monastery"]
PACKAGE_TYPES = ["Family", "Individual", "Group", "Singles"]
LANGUAGES = ["English", "Polish"]

CUSTOMER_NAME = "[CUSTOMER_NAME]"
TOUR_GUIDE = "[TOUR_GUIDE]"
PLACEHOLDERS = [CUSTOMER_NAME, TOUR_GUIDE]


@dataclass(frozen=True, order=True)
class TemplateKey:
    """The combination of attributes one template is written for."""

    destination: str
    package_type: str
    language: str

    def label(self) -> str:
        return f"{self.destination} / {self.package_type} / {self.language}"


def all_keys() -> list[TemplateKey]:
    """Every template key: 3 destinations x 4 package types x 2 languages = 24."""
    return [TemplateKey(d, p, l) for d, p, l in product(DESTINATIONS, PACKAGE_TYPES, LANGUAGES)]
