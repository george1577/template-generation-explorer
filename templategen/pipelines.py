"""One function per step of the pattern. Wires a Writer to the store, checks and fill."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .catalog import CUSTOMER_NAME, TOUR_GUIDE, TemplateKey
from .checks import Finding, run_checks
from .fill import FillResult, check_customer_value, fill
from .prompts import live_prompt, template_prompt
from .store import APPROVED, TemplateStore

Writer = Callable[[str], str]


# ------------------------------------------------------------------ ① generate one template


@dataclass
class Generation:
    key: TemplateKey
    prompt: str
    text: str
    findings: list[Finding]
    seconds: float


def generate_template(write: Writer, key: TemplateKey, prompt: str | None = None) -> Generation:
    prompt = prompt if prompt is not None else template_prompt(key)
    start = time.perf_counter()
    text = write(prompt)
    seconds = time.perf_counter() - start
    return Generation(key, prompt, text, run_checks(text, key.language), seconds)


# ------------------------------------------------------------------ ② build the store


@dataclass
class BuildReport:
    generated: list[TemplateKey] = field(default_factory=list)
    skipped: list[TemplateKey] = field(default_factory=list)
    failed: dict[TemplateKey, str] = field(default_factory=dict)
    seconds: float = 0.0


def build_store(
    store: TemplateStore,
    write: Writer,
    model_name: str,
    keys: list[TemplateKey],
    only_missing: bool,
    on_progress: Callable[[int, int, TemplateKey], None] | None = None,
) -> BuildReport:
    """Generate a template for each key and save it as pending.

    only_missing=True skips keys that already have a template (and keeps their review status).
    """
    report = BuildReport()
    start = time.perf_counter()
    for i, key in enumerate(keys):
        if on_progress:
            on_progress(i, len(keys), key)
        if only_missing and store.get(key) is not None:
            report.skipped.append(key)
            continue
        try:
            store.put(key, write(template_prompt(key)), model_name)
            report.generated.append(key)
        except Exception as exc:  # one failure shouldn't stop the batch
            report.failed[key] = str(exc)
    report.seconds = time.perf_counter() - start
    return report


# ------------------------------------------------------------------ ③ review


def regenerate(store: TemplateStore, write: Writer, model_name: str, key: TemplateKey) -> str:
    """Replace a (usually rejected) template with a fresh one. It goes back to pending."""
    text = write(template_prompt(key))
    store.put(key, text, model_name)
    return text


# ------------------------------------------------------------------ ④ send


@dataclass
class LiveRun:
    prompt: str
    letter: str
    seconds: float


@dataclass
class Comparison:
    live_runs: list[LiveRun]
    filled: FillResult | None  # None when there is no approved template for the key
    fill_seconds: float
    template_status: str | None
    name_warnings: list[str]
    guide_warnings: list[str]


def fill_letter(store: TemplateStore, key: TemplateKey, customer: str, guide: str):
    """Fill the approved template for a key. Returns (FillResult | None, status | None)."""
    stored = store.get(key)
    if stored is None or stored.status != APPROVED:
        return None, (stored.status if stored else None)
    return fill(stored.text, {CUSTOMER_NAME: customer, TOUR_GUIDE: guide}), APPROVED


def compare_live_vs_fill(
    store: TemplateStore,
    write: Writer | None,
    key: TemplateKey,
    customer: str,
    guide: str,
    live_runs: int = 2,
) -> Comparison:
    """Write the same customer's letter both ways: live generation (N times) and fill (once)."""
    runs = []
    if write is not None:
        prompt = live_prompt(key, customer, guide)
        for _ in range(live_runs):
            start = time.perf_counter()
            letter = write(prompt)
            runs.append(LiveRun(prompt, letter, time.perf_counter() - start))
    start = time.perf_counter()
    filled, status = fill_letter(store, key, customer, guide)
    fill_seconds = time.perf_counter() - start
    return Comparison(
        runs, filled, fill_seconds, status, check_customer_value(customer), check_customer_value(guide)
    )


@dataclass
class Customer:
    name: str
    guide: str
    key: TemplateKey


@dataclass
class SendOutcome:
    customer: Customer
    sent: bool
    reason: str  # why it was held, or "sent"
    letter: str = ""
    warnings: list[str] = field(default_factory=list)


def load_customers(path: str | Path) -> list[Customer]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Customer(r["name"], r["guide"], TemplateKey(r["destination"], r["package_type"], r["language"]))
        for r in records
    ]


def send_all(store: TemplateStore, customers: list[Customer]) -> tuple[list[SendOutcome], float]:
    """Fill a letter for every customer whose template is approved; hold back the rest."""
    start = time.perf_counter()
    outcomes = []
    for c in customers:
        warnings = check_customer_value(c.name) + check_customer_value(c.guide)
        filled, status = fill_letter(store, c.key, c.name, c.guide)
        if filled is None:
            reason = "no template for this key" if status is None else f"template is {status}"
            outcomes.append(SendOutcome(c, False, reason, warnings=warnings))
        elif filled.leftovers:
            outcomes.append(
                SendOutcome(c, False, f"unfilled placeholders: {', '.join(filled.leftovers)}",
                            filled.letter, warnings)
            )
        elif warnings:
            outcomes.append(SendOutcome(c, False, "customer details look wrong", filled.letter, warnings))
        else:
            outcomes.append(SendOutcome(c, True, "sent", filled.letter))
    return outcomes, time.perf_counter() - start
