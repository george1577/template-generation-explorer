"""The template store: one template per template key, with its review status, in SQLite."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .catalog import TemplateKey

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
STATUSES = [PENDING, APPROVED, REJECTED]

SCHEMA = """
CREATE TABLE IF NOT EXISTS templates (
    destination  TEXT NOT NULL,
    package_type TEXT NOT NULL,
    language     TEXT NOT NULL,
    text         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    model        TEXT NOT NULL DEFAULT '',
    edited       INTEGER NOT NULL DEFAULT 0,
    note         TEXT NOT NULL DEFAULT '',
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (destination, package_type, language)
)
"""


@dataclass
class StoredTemplate:
    key: TemplateKey
    text: str
    status: str
    model: str
    edited: bool  # a reviewer changed the text by hand
    note: str  # the reviewer's reason, e.g. why it was rejected
    updated_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TemplateStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute(SCHEMA)
        self._db.commit()

    # ------------------------------------------------------------------ reads

    def get(self, key: TemplateKey) -> StoredTemplate | None:
        row = self._db.execute(
            "SELECT * FROM templates WHERE destination=? AND package_type=? AND language=?",
            (key.destination, key.package_type, key.language),
        ).fetchone()
        return self._row(row) if row else None

    def all(self) -> list[StoredTemplate]:
        rows = self._db.execute(
            "SELECT * FROM templates ORDER BY destination, package_type, language"
        ).fetchall()
        return [self._row(r) for r in rows]

    def counts(self) -> dict[str, int]:
        counts = {s: 0 for s in STATUSES}
        for status, n in self._db.execute(
            "SELECT status, COUNT(*) FROM templates GROUP BY status"
        ):
            counts[status] = n
        return counts

    # ------------------------------------------------------------------ writes

    def put(self, key: TemplateKey, text: str, model: str) -> None:
        """Save a newly generated template. It always starts (or starts again) as pending."""
        self._db.execute(
            "INSERT OR REPLACE INTO templates VALUES (?, ?, ?, ?, ?, ?, 0, '', ?)",
            (key.destination, key.package_type, key.language, text, PENDING, model, _now()),
        )
        self._db.commit()

    def edit(self, key: TemplateKey, text: str) -> None:
        """A reviewer changed the text. It goes back to pending: edits need approving too."""
        self._update(key, text=text, status=PENDING, edited=1)

    def set_status(self, key: TemplateKey, status: str, note: str = "") -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status {status!r}")
        self._update(key, status=status, note=note)

    def clear(self) -> None:
        self._db.execute("DELETE FROM templates")
        self._db.commit()

    # ------------------------------------------------------------------ seed / export

    def load_json(self, path: str | Path) -> int:
        """Replace everything with templates from a JSON file (the bundled seed or an export)."""
        records = json.loads(Path(path).read_text(encoding="utf-8"))
        self.clear()
        for r in records:
            self._db.execute(
                "INSERT INTO templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["destination"], r["package_type"], r["language"], r["text"],
                    r.get("status", PENDING), r.get("model", ""), int(r.get("edited", 0)),
                    r.get("note", ""), r.get("updated_at", _now()),
                ),
            )
        self._db.commit()
        return len(records)

    def to_json(self) -> str:
        records = []
        for t in self.all():
            d = asdict(t)
            d.update(asdict(t.key))
            del d["key"]
            records.append(d)
        return json.dumps(records, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ internals

    def _update(self, key: TemplateKey, **fields) -> None:
        if self.get(key) is None:
            raise KeyError(f"No template for {key.label()}")
        fields["updated_at"] = _now()
        sets = ", ".join(f"{k}=?" for k in fields)
        self._db.execute(
            f"UPDATE templates SET {sets} WHERE destination=? AND package_type=? AND language=?",
            (*fields.values(), key.destination, key.package_type, key.language),
        )
        self._db.commit()

    @staticmethod
    def _row(row) -> StoredTemplate:
        d, p, l, text, status, model, edited, note, updated_at = row
        return StoredTemplate(TemplateKey(d, p, l), text, status, model, bool(edited), note, updated_at)
