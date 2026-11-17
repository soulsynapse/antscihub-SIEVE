"""What every tool's settings widget holds, what every document under a folder loads to, and what
every tool raises of a choice it does not offer, written as one JSON file; with a third argument,
compared with a file written before, a part at a time.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-a-param-declared-once.py video-tests out.json [before.json]

A widget is the tool's `settings()` where it has one and the player's of its declaration where it
has none, so the script runs on a tree of either. A refusal is the tool's computing handed its
defaults with the one choice replaced, over a table and planes made here; one whose text is not the
tool's refusal is marked, the inputs made here having failed it first."""
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit, QSlider  # noqa: E402

from sieve_player import document, registry  # noqa: E402
from sieve_player.graph import Series  # noqa: E402
from sieve_player.widgets import ChoiceList, ParamWidget, ValueField  # noqa: E402

NOT_OFFERED = "not offered"
ROWS = 6
NOTHING = "raised nothing"
FED = {"resolve": {"columns": "area"}}   # a column the table made here has


def widget_of(tool):
    make = getattr(tool, "settings", None)
    return make() if make is not None else ParamWidget.declared(registry.params(tool))


def row(w):
    if isinstance(w, ChoiceList):
        return ["list"]
    if isinstance(w, QCheckBox):
        return ["bool"]
    if isinstance(w, QComboBox):
        return ["choice", [w.itemText(i) for i in range(w.count())], w.isEditable()]
    if isinstance(w, QLineEdit):
        return ["text"]
    s, shown = w.findChild(QSlider), w.findChild(ValueField)
    return ["slider", s.minimum(), s.maximum(), shown.text()]


def widgets(tools):
    out = {}
    for name, tool in tools.items():
        w = widget_of(tool)
        out[name] = {"rows": [[n, *row(r)] for n, r in w._rows.items()], "params": w.params(), "order": list(w.params()),
                     "defaults": registry.defaults(tool)}
        w.deleteLater()
    return out


def loaded(folder, tools):
    out = {}
    for root, _, names in sorted(os.walk(folder)):
        for name in sorted(names):
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if name.endswith(".json") and isinstance(d, dict) and "nodes" in d:
                out[path.replace(os.sep, "/")] = {n.id: n.params for n in document.load(path, tools).nodes}
    return out


def planes(tools):
    """Type -> a value of it at each of ROWS rows."""
    rng = np.random.default_rng(0)
    gray = [rng.integers(0, 255, (48, 64), np.uint8) for _ in range(ROWS)]
    mask = []
    for r in range(ROWS):
        m = np.zeros((48, 64), np.uint8)
        m[10:20, 5 + 2 * r:15 + 2 * r] = 255
        m[30:38, 40:50] = 255
        mask.append(m)
    blobs = [tools["blobs"].run(lambda row, name=None, m=m: m, 0, {**registry.defaults(tools["blobs"]), "min_area": 2}) for m in mask]
    table = np.empty(ROWS, object)
    table[:] = blobs
    tracks = tools["track"].run(Series(table, "k", 0, 30.0), {**registry.defaults(tools["track"]), "max_step": 5.0, "min_rows": 1})["rows"]
    return {"gray": gray, "mask": mask, "bgr": [np.dstack([g, g, g]) for g in gray], "hsv": [np.dstack([g, g, g]) for g in gray],
            "flow": [rng.normal(size=(48, 64, 2)).astype(np.float32) for _ in range(ROWS)],
            "blobs": blobs, "tracks": list(tracks), "signal": [float(r) for r in range(ROWS)]}


def refusal(tool, params, have):
    first = next(t for t in registry.expects(tool) if t in have)
    more = {n: next(t for t in ts if t in have) for n, ts in registry.inputs(tool).items()}
    try:
        if registry.kind(tool) == "series":
            fold = registry.fold_of(tool)
            if fold is not None:
                data = np.stack([fold(v) for v in have[first]])
            elif first == "signal":
                data = np.array(have[first], float)
            else:
                data = np.empty(ROWS, object)
                for i, v in enumerate(have[first]):
                    data[i] = v
            tool.run(Series(data, "k", 0, 30.0), params)
        else:
            def frames(row, name=None):
                return have[more[name] if name else first][row % ROWS]
            frames.count = ROWS
            tool.run(frames, 0, params)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return NOTHING


def refusals(tools, shown):
    have, out = planes(tools), {}
    for name, tool in tools.items():
        for param, kind, *rest in shown[name]["rows"]:
            if kind == "choice" and not rest[1] and registry.expects(tool) is not None:
                said = refusal(tool, {**registry.defaults(tool), **FED.get(name, {}), param: NOT_OFFERED}, have)
                out[f"{name}.{param}"] = said if NOT_OFFERED in said or said == NOTHING else f"NOT THE REFUSAL: {said}"
    return out


def main(folder, out, before=None):
    app = QApplication.instance() or QApplication([])  # noqa: F841
    tools = {e.name: e.module for e in registry.discover("tools") if e.ok}
    shown = widgets(tools)
    now = json.loads(json.dumps({"widgets": shown, "loaded": loaded(folder, tools), "refusals": refusals(tools, shown)}))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(now, f, indent=1, sort_keys=True)
    for part, n in ((p, len(now[p])) for p in now):
        print(f"{part}: {n}")
    for k, said in now["refusals"].items():
        if said.startswith("NOT"):
            print(f"  {k}: {said}")
    if before is None:
        return 0
    with open(before, encoding="utf-8") as f:
        was = json.load(f)
    differ = 0
    for part in now:
        for k in sorted(set(now[part]) | set(was[part])):
            a, b = was[part].get(k), now[part].get(k)
            same = a == b
            if not same:
                differ += 1
                print(f"DIFFERS {part} {k}\n  was {a}\n  now {b}")
    print("equal to the file written before" if not differ else f"{differ} differ")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
