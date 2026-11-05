"""Series tool: the identity pass over finished tracklets; tracks in, tracks out with `identity` and
`conflict` columns.

An id is an identity where at least `min_reads` reads agree and none disagree; it is that identity on
every row it holds. A read is a non-NaN value of one of `columns`, which share one identity space, or
a row of `labels`, (first row, last row, id, identity), on each of the id's rows in the span. Two
identities on one id, or one already held by an overlapping id with more reads, leave it NaN and
flagged. Where two ids end as one starts over their last centroids and it ends as two start inside
its last box, the identities entering and leaving are one set, and the one unlabelled id on a side
takes the identity the other side has that its own lacks. `main` is the same pass over a tracks csv.
"""
import os
import re

import numpy as np

from tools import csv
from tools.blobs import with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "resolve", "series", "tracks", "tracks"
SIGNALS = ("identities", "conflicts")
IDENTITY, CONFLICT = "identity", "conflict"
DEFAULTS = {"columns": "tag_code", "min_reads": 2, "signal": "identities", "labels": []}
PATHS = {"labels": lambda path: {"labels": load_labels(path)}}
MAX_READS = 1000


def names(text):
    return [c.strip() for c in str(text).split(",") if c.strip()]


def load_labels(path):
    """The rows of a csv of first row, last row, id, identity, as lists; a '#' line or a header is
    skipped, and any other line not of four numbers raises."""
    out, header = [], True
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            parts = [p.strip() for p in line.strip().split(",")]
            if parts == [""] or parts[0].startswith("#"):
                continue
            try:
                row = [int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])] if len(parts) == 4 else None
            except ValueError:
                row = None
                if header and not out:
                    header = False
                    continue
            if row is None:
                raise ValueError(f"{os.path.basename(path)} line {n}: first row, last row, id, identity expected")
            header = False
            out.append(row)
    return out


def reads_of(rows, columns, labels, start):
    reads, spans, labelled = {}, {}, {}
    for a, last, i, z in labels:
        labelled.setdefault(i, []).append((a, last, z))
    for r, t in enumerate(rows):
        for c in columns:
            if len(t) and c not in t.dtype.names:
                raise ValueError(f"resolve: no column {c!r}; one of {t.dtype.names}")
        for b in t:
            id = int(b["id"])
            spans.setdefault(id, set()).add(r)
            count = reads.setdefault(id, {})
            for v in [float(b[c]) for c in columns] + [float(z) for a, last, z in labelled.get(id, ()) if a <= r + start <= last]:
                if not np.isnan(v):
                    count[v] = count.get(v, 0) + 1
    return reads, spans


def contacts(rows):
    """[(ids ending as one id starts over their last centroids, ids starting inside its last box)],
    one per id with as many entering as leaving and at least two; none where the tables lack boxes."""
    first, last = {}, {}
    for r, t in enumerate(rows):
        if len(t) and not {"x", "y", "w", "h", "cx", "cy"} <= set(t.dtype.names):
            return []
        for b in t:
            first.setdefault(int(b["id"]), (r, b))
            last[int(b["id"])] = (r, b)

    def inside(b, box):
        return box["x"] <= b["cx"] <= box["x"] + box["w"] and box["y"] <= b["cy"] <= box["y"] + box["h"]

    ending, starting = {}, {}       # row -> the ids whose last, or first, record is there
    for i, (r, _) in last.items():
        ending.setdefault(r, []).append(i)
    for i, (r, _) in first.items():
        starting.setdefault(r, []).append(i)
    out = []
    for c, (r0, b0) in first.items():
        r1, b1 = last[c]
        ins = [i for i in ending.get(r0 - 1, ()) if inside(last[i][1], b0)]
        outs = [i for i in starting.get(r1 + 1, ()) if inside(first[i][1], b1)]
        if len(ins) >= 2 and len(ins) == len(outs):
            out.append((ins, outs))
    return out


def resolve(rows, columns, min_reads=2, labels=(), start=0):
    reads, spans = reads_of(rows, columns, labels, start)
    identity, flagged = {}, set()
    for id, count in reads.items():
        if len(count) > 1:
            flagged.add(id)
        elif len(count) == 1 and next(iter(count.values())) >= min_reads:
            identity[id] = next(iter(count))
    for v in set(identity.values()):
        held = []
        for i in sorted((i for i in identity if identity[i] == v), key=lambda i: (-reads[i][v], min(spans[i]))):
            if any(spans[i] & spans[j] for j in held):
                del identity[i]
                flagged.add(i)
            else:
                held.append(i)
    for ins, outs in contacts(rows):
        settled = False
        while not settled:
            settled = True
            for side, other in ((ins, outs), (outs, ins)):
                unknown = [i for i in side if i not in identity]
                if len(unknown) == 1:
                    missing = {identity[j] for j in other if j in identity} - {identity[i] for i in side if i in identity}
                    if len(missing) == 1:
                        identity[unknown[0]], settled = missing.pop(), False
    out = np.empty(len(rows), object)
    out[:] = [with_column(with_column(t, IDENTITY, np.array([identity.get(int(i), np.nan) for i in t["id"]], np.float64)),
                          CONFLICT, np.array([int(i) in flagged for i in t["id"]], np.int32)) for t in rows]
    return out


def signal(rows, kind):
    if kind not in SIGNALS:
        raise ValueError(f"resolve: no signal {kind!r}; one of {SIGNALS}")
    if kind == "identities":
        return np.array([len({float(v) for v in t[IDENTITY] if not np.isnan(v)}) for t in rows], np.float32)
    return np.array([int(t[CONFLICT].sum()) for t in rows], np.float32)


def run(series, params):
    rows = resolve(series.data, names(params["columns"]), int(params["min_reads"]), params.get("labels") or [], series.start)
    return {"rows": rows, "signal": signal(rows, params["signal"])}


def draw(painter, row, result, start, params):
    from tools import track

    track.draw(painter, row, result, start, params)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("columns", DEFAULTS["columns"])
    w.add_int("min_reads", 1, MAX_READS, DEFAULTS["min_reads"])
    w.add_choice("signal", SIGNALS, DEFAULTS["signal"])
    return w


def tables_of(header, lines, start, n):
    """One table per row of `start`..`start + n - 1` from a tracks csv's split lines: `id` as int32,
    every column but row, time and gate as float64."""
    fields = [c for c in header if c not in ("row", "time", "gate")]
    dtype = np.dtype([(c, np.int32 if c == "id" else np.float64) for c in fields])
    at = {c: header.index(c) for c in fields}
    per_row = {r: [] for r in range(start, start + n)}
    for parts in lines:
        per_row[int(parts[header.index("row")])].append(tuple(int(parts[at["id"]]) if c == "id" else float(parts[at[c]]) for c in fields))
    out = np.empty(n, object)
    out[:] = [np.array(per_row[r], dtype) for r in range(start, start + n)]
    return out


def rewrite(path, columns, min_reads=2, labels=(), out=None):
    """The tracks csv at `path` with `identity` and `conflict` written before `gate` on every line,
    replacing a previous pass's, the key line kept; written to `out` or over `path`."""
    with open(path, encoding="utf-8") as f:
        key = f.readline().rstrip("\n")
        header = f.readline().rstrip("\n").split(",")
        lines = [line.rstrip("\n").split(",") for line in f if line.strip()]
    m = re.search(r"rows=(\d+)-(\d+)", key)
    if not m:
        raise ValueError(f"{os.path.basename(path)} has no sieve key line; is it a tracks csv?")
    keep = [i for i, c in enumerate(header) if c not in (IDENTITY, CONFLICT)]
    header, lines = [header[i] for i in keep], [[p[i] for i in keep] for p in lines]
    start, n = int(m.group(1)), int(m.group(2)) - int(m.group(1)) + 1
    rows = resolve(tables_of(header, lines, start, n), columns, min_reads, labels, start)
    value = {(start + r, int(b["id"])): (float(b[IDENTITY]), int(b[CONFLICT])) for r, t in enumerate(rows) for b in t}
    g, at_row, at_id = header.index("gate"), header.index("row"), header.index("id")
    text = [key, ",".join(header[:g] + [IDENTITY, CONFLICT] + header[g:])]
    for p in lines:
        ident, conf = value[(int(p[at_row]), int(p[at_id]))]
        text.append(",".join(p[:g] + [np.format_float_positional(ident, trim="-"), str(conf)] + p[g:]))
    csv.replace(out or path, "\n".join(text) + "\n")


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(prog="python -m tools.resolve",
                                 description="the identity pass over a tracks csv, written back with identity and conflict columns")
    ap.add_argument("tracks", help="a csv tracks-csv wrote")
    ap.add_argument("--columns", default=DEFAULTS["columns"], help="observation columns, comma separated")
    ap.add_argument("--min-reads", type=int, default=DEFAULTS["min_reads"])
    ap.add_argument("--labels", help="a csv of first row, last row, id, identity")
    ap.add_argument("--out", help="write here instead of over the input")
    a = ap.parse_args(argv)
    rewrite(a.tracks, names(a.columns), a.min_reads, load_labels(a.labels) if a.labels else [], a.out)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
