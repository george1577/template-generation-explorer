"""Generate the bundled seed: one template per template key, all pending review.

    uv run python scripts/make_seed.py                         # qwen2.5:3b via Ollama
    uv run python scripts/make_seed.py "Ollama · qwen2.5:7b"
    uv run python scripts/make_seed.py --fresh                 # ignore an existing seed file

The file is saved after every template, and a re-run skips keys already in it, so an
interrupted run can simply be started again. Each template is retried up to 3 times.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from templategen.catalog import all_keys  # noqa: E402
from templategen.llm import make_writer  # noqa: E402
from templategen.prompts import template_prompt  # noqa: E402

args = [a for a in sys.argv[1:] if a != "--fresh"]
fresh = "--fresh" in sys.argv
choice = args[0] if args else "Ollama · qwen2.5:3b"
writer = make_writer(choice)
out = Path(__file__).resolve().parent.parent / "data" / "seed_templates.json"

records = [] if fresh or not out.exists() else json.loads(out.read_text(encoding="utf-8"))
done = {(r["destination"], r["package_type"], r["language"]) for r in records}


def save() -> None:
    order = {(k.destination, k.package_type, k.language): i for i, k in enumerate(all_keys())}
    records.sort(key=lambda r: order[(r["destination"], r["package_type"], r["language"])])
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


failed_in_a_row = 0
for i, key in enumerate(all_keys(), 1):
    if (key.destination, key.package_type, key.language) in done:
        print(f"[{i:2}/24] {key.label()}  (already done)", flush=True)
        continue
    print(f"[{i:2}/24] {key.label()}", flush=True)
    for attempt in range(1, 4):
        try:
            text = writer(template_prompt(key))
            break
        except Exception as exc:
            print(f"        attempt {attempt} failed: {str(exc)[:160]}", flush=True)
            time.sleep(20 * attempt)  # give rate limits (HTTP 429) time to reset
    else:
        print("        giving up on this key; re-run the script to try again", flush=True)
        failed_in_a_row += 1
        if failed_in_a_row == 3:
            sys.exit("3 keys in a row failed; stopping. Check the model name, key or server.")
        continue
    failed_in_a_row = 0
    records.append({
        "destination": key.destination,
        "package_type": key.package_type,
        "language": key.language,
        "text": text,
        "status": "pending",
        "model": writer.name,
        "edited": False,
        "note": "",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    save()

print(f"{len(records)}/24 templates in {out}")
