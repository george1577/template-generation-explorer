import json

import pytest

from templategen.catalog import TemplateKey, all_keys
from templategen.store import APPROVED, PENDING, REJECTED, TemplateStore

KEY = TemplateKey("Toledo, Spain", "Family", "English")


@pytest.fixture
def store():
    return TemplateStore(":memory:")


def test_all_keys_is_the_full_grid():
    keys = all_keys()
    assert len(keys) == 24 and len(set(keys)) == 24


def test_new_templates_start_pending(store):
    store.put(KEY, "text", "fake")
    assert store.get(KEY).status == PENDING


def test_approve_then_edit_goes_back_to_pending(store):
    store.put(KEY, "text", "fake")
    store.set_status(KEY, APPROVED)
    store.edit(KEY, "better text")
    t = store.get(KEY)
    assert (t.text, t.status, t.edited) == ("better text", PENDING, True)


def test_regenerating_resets_review(store):
    store.put(KEY, "text", "fake")
    store.set_status(KEY, REJECTED, note="mentions a price")
    store.put(KEY, "new text", "fake")
    t = store.get(KEY)
    assert (t.status, t.note, t.edited) == (PENDING, "", False)


def test_counts(store):
    for k in all_keys()[:3]:
        store.put(k, "t", "fake")
    store.set_status(all_keys()[0], APPROVED)
    assert store.counts() == {PENDING: 2, APPROVED: 1, REJECTED: 0}


def test_json_round_trip(store, tmp_path):
    store.put(KEY, "Dear [CUSTOMER_NAME] – zażółć", "fake")
    store.set_status(KEY, APPROVED)
    path = tmp_path / "export.json"
    path.write_text(store.to_json(), encoding="utf-8")
    other = TemplateStore(":memory:")
    assert other.load_json(path) == 1
    assert other.get(KEY) == store.get(KEY)
    assert json.loads(path.read_text(encoding="utf-8"))[0]["destination"] == "Toledo, Spain"


def test_unknown_status_and_key_raise(store):
    with pytest.raises(KeyError):
        store.set_status(KEY, APPROVED)
    store.put(KEY, "t", "fake")
    with pytest.raises(ValueError):
        store.set_status(KEY, "maybe")
