"""Derive a contract-carrying name for every tool from the registry's facets, and print the table in
docs/naming-generated.md. FAMILY is the one facet no tool declares; it is assigned here by hand, and
a tool without one is written with `?` rather than stopping the table. Run from the repo root."""
import sys

sys.path.insert(0, ".")
from sieve_player.registry import discover  # noqa: E402

CLASSES = {
    "plane": {"bgr", "gray", "hsv", "mask", "flow"},
    "table": {"blobs", "tracks"},
}
ALL = set().union(*CLASSES.values()) | {"signal", "path"}

FAMILY = {
    "file": "source", "region": "source",
    "gray": "convert", "hsv": "convert", "threshold": "convert", "inrange": "convert",
    "blobs": "convert", "blobs-to-mask": "convert", "flow": "convert", "track": "convert",
    "speed": "convert", "agreement": "convert",
    "crop": "transform", "rescale": "transform", "mask": "transform", "bg-subtract": "transform",
    "background": "transform", "morphology": "transform", "combine": "transform",
    "coarsegrain": "transform", "motion": "transform", "changeenergy": "transform",
    "smooth": "transform",
    "bake": "cache",
    "filter": "select", "tracks-filter": "select",
    "attach": "transfer", "inside": "transfer", "sample": "transfer", "decode": "transfer",
    "resolve": "transfer", "kinematics": "transfer",
    "count": "measure", "size": "measure", "spacing": "measure", "reduce": "measure",
    "transitions": "measure", "travel": "measure",
    "csv": "sink", "tracks-csv": "sink",
}

# the operation word once the type words the current name carries are removed
OP = {"gray": "gray", "hsv": "hsv", "blobs-to-mask": "paint", "blobs": "blobs", "tracks-filter": "filter",
      "tracks-csv": "csv", "bg-subtract": "subtract"}


def as_set(ex):
    if ex is None:
        return set()
    return {ex} if isinstance(ex, str) else set(ex)


def classify(ts):
    """One word for a set of types, and whether the word overstates it."""
    if not ts:
        return "", ""
    if len(ts) == 1:
        return next(iter(ts)), ""
    if ts == ALL:
        return "any", ""
    for name, members in CLASSES.items():
        if ts == members:
            return name, ""
        if ts < members:
            return name, f"{name} minus {'/'.join(sorted(members - ts))}"
    return "-or-".join(sorted(ts)), "spans classes"


def row(e):
    name = e.name
    expects, inputs, paths = as_set(e.get("EXPECTS")), e.get("INPUTS") or {}, e.get("PATHS") or {}
    produces = e.get("PRODUCES")
    primary, strain = classify(expects)
    secondary = [classify(as_set(t))[0] for t in inputs.values()] + (["path"] if paths else [])
    fam = FAMILY.get(name, "?")
    op = OP.get(name, name)
    out = produces if produces else "?"
    head = "-and-".join([primary] + secondary) if primary else "-and-".join(secondary) or "none"
    literal = f"{head}-{fam}-{op}-to-{out}"
    if fam == "convert" and op == out:
        trimmed = f"{head}-to-{out}"
    elif fam == "convert":
        trimmed = f"{head}-{op}-to-{out}"
    elif fam in ("transform", "cache", "select", "transfer") and out == "same" or out == primary:
        trimmed = f"{head}-{fam}-{op}" if fam != "transform" else f"{head}-{op}"
    elif fam == "measure" and out == "signal":
        trimmed = f"{head}-measure-{op}"
    else:
        trimmed = literal
    contract = " + ".join(["/".join(sorted(expects)) or "-"] + [f"{k}:{v}" for k, v in inputs.items()]
                          + [f"{k}:path" for k in paths]) + f" -> {out}"
    notes = [s for s in [strain, "no family" if fam == "?" else ""] if s]
    return name, contract, fam, literal, trimmed, "; ".join(notes)


def main():
    rows = [row(e) for e in discover("tools") if e.ok]
    print("| current | contract | family | literal grammar | trimmed | strain |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(f"`{c}`" if i in (1, 3, 4) else c for i, c in enumerate(r)) + " |")


if __name__ == "__main__":
    main()
