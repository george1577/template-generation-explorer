"""Prompts, adapted from the reference notebook."""

from __future__ import annotations

from .catalog import TemplateKey

# The notebook's system prompt for its zero_shot() helper.
SYSTEM_PROMPT = "In your responses, do not include any preamble."

# The notebook's create_template() prompt, with its indentation removed.
TEMPLATE_PROMPT = """\
You are a tour guide working on behalf of Tours GenAI S.L.
Write a personalized letter in {language} to a customer who has purchased a
{package_type} tour package to visit {destination}.
Sound excited to see them and lead them on the tour.
Explain some of the highlights of what they will see there and some of the things they can do while there.
In the letter, use [CUSTOMER_NAME] to indicate the place to be replaced by their name
and [TOUR_GUIDE] to indicate the place to be replaced by your name."""

# Live generation: the same request, but with the real names put straight into the prompt.
# This is the approach the pattern avoids. It is here only for comparison.
LIVE_PROMPT = """\
You are a tour guide working on behalf of Tours GenAI S.L.
Write a personalized letter in {language} to a customer who has purchased a
{package_type} tour package to visit {destination}.
Sound excited to see them and lead them on the tour.
Explain some of the highlights of what they will see there and some of the things they can do while there.
The customer's name is {customer_name}.
Your name is {tour_guide}."""


def template_prompt(key: TemplateKey) -> str:
    return TEMPLATE_PROMPT.format(
        language=key.language, package_type=key.package_type, destination=key.destination
    )


def live_prompt(key: TemplateKey, customer_name: str, tour_guide: str) -> str:
    return LIVE_PROMPT.format(
        language=key.language,
        package_type=key.package_type,
        destination=key.destination,
        customer_name=customer_name,
        tour_guide=tour_guide,
    )
