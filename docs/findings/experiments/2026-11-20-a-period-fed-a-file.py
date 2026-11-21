"""The one-off of docs/spec/a-cut-in-time.md's box of a `period` fed a file: a file of touching and
overlapping periods and a file of each refusal, what `load_periods` makes of each, and the cuts the
plan gives the node and a node below it, against the file.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-period-fed-a-file.py

No video is read: the plan is pure in the document and the tools.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import document as D  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from sieve_player.registry import discover  # noqa: E402

GOOD = {"rows": 300, "made by": "a hand", "periods": [
    {"name": "a", "first": 0, "end": 100}, {"name": "b", "first": 100, "end": 150},
    {"name": "c", "first": 120, "end": 300}]}
REFUSED = {
    "not json": "{rows: 300",
    "a repeated name": {"rows": 300, "periods": [{"name": "a", "first": 0, "end": 10}, {"name": "a", "first": 5, "end": 20}]},
    "a period of no rows": {"rows": 300, "periods": [{"name": "a", "first": 40, "end": 40}]},
    "one past the footage's rows": {"rows": 300, "periods": [{"name": "a", "first": 250, "end": 301}]},
}


def main():
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    period = tools["period"]
    with tempfile.TemporaryDirectory() as folder:
        def written(name, body):
            path = os.path.join(folder, f"{name}.json")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(body if isinstance(body, str) else json.dumps(body))
            return path

        params = period.load_periods(written("good", GOOD))
        print("file:   ", [(p["name"], p["first"], p["end"]) for p in GOOD["periods"]])
        print("loaded: ", [(p["name"], p["first"], p["end"]) for p in params["periods"]], "rows", params["rows"])
        for what, body in REFUSED.items():
            try:
                period.load_periods(written(what.replace(" ", "-").replace("'", ""), body))
                print(f"{what}: taken, NOT refused")
            except ValueError as e:
                print(f"{what}: {type(e).__name__}: {e}")

    doc = D.from_tools([tools["gray"], period, tools["gray"]])
    cutting, below = doc.nodes[2].id, doc.nodes[3].id
    doc.node(cutting).params.update(params)
    doc.connect(cutting, below)
    entries = plan(doc, tools, "video key").entries
    print("the period's cuts:  ", [r.extent.rows for r in entries[cutting].cuts])
    print("a node below's cuts:", [r.extent.rows for r in entries[below].cuts], "made from", [len(r.made_from) for r in entries[below].cuts])
    print("its key in params:  ", period.key_params(params))


if __name__ == "__main__":
    main()
