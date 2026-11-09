"""Talking to the model. The only module that imports pydantic-ai.

Everything else receives a `Writer`: a function that takes a prompt and returns text.
That keeps the pattern's logic testable with a fake writer and no model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from .prompts import SYSTEM_PROMPT

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

TEMPERATURE = 0.1  # the notebook's setting ("not too creative??")
MAX_TOKENS = 1200  # a letter is ~400-600 tokens; this stops a small model that starts rambling

# Label shown in the sidebar -> (provider, model name)
MODEL_CHOICES: dict[str, tuple[str, str]] = {
    "Ollama · qwen2.5:3b": ("ollama", "qwen2.5:3b"),
    "Ollama · qwen2.5:7b": ("ollama", "qwen2.5:7b"),
    "Ollama · qwen2.5:1.5b": ("ollama", "qwen2.5:1.5b"),
    "Gemini · gemini-3.6-flash": ("gemini", "gemini-3.6-flash"),
    "Gemini · gemini-3.5-flash": ("gemini", "gemini-3.5-flash"),
}
DEFAULT_CHOICE = "Ollama · qwen2.5:3b"


@dataclass
class Writer:
    """A named prompt -> text function."""

    name: str
    write: Callable[[str], str]

    def __call__(self, prompt: str) -> str:
        return self.write(prompt).strip()


def make_writer(choice: str) -> Writer:
    """Build a Writer for a sidebar choice. Mirrors the notebook's zero_shot() helper."""
    from pydantic_ai import Agent

    provider, model_name = MODEL_CHOICES[choice]
    if provider == "ollama":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.ollama import OllamaProvider

        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = OpenAIChatModel(model_name, provider=OllamaProvider(base_url=base_url))
        settings = {"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS}
    elif provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set GEMINI_API_KEY (in the environment or a keys.env file) to use Gemini."
            )
        from google.genai.types import HttpRetryOptions

        # Fail fast when Gemini is overloaded instead of retrying silently for minutes.
        provider_ = GoogleProvider(api_key=api_key, retry_options=HttpRetryOptions(attempts=2))
        model = GoogleModel(model_name, provider=provider_)
        # Writing a letter needs no reasoning. Gemini 3.x thinks by default, which is slow and,
        # with a token cap, can leave too little room for the letter itself. So: low thinking, no cap.
        settings = {"temperature": TEMPERATURE, "google_thinking_config": {"thinking_level": "low"}}
    else:  # pragma: no cover
        raise ValueError(provider)

    agent = Agent(model, system_prompt=SYSTEM_PROMPT, model_settings=settings)
    return Writer(name=model_name, write=lambda prompt: agent.run_sync(prompt).output)
