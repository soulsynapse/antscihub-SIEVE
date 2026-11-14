r"""The catalogue's findings as text: `report`, one block for the entries a reader copies out of the
monitor; `text`, one entry with enough beside it to begin on its fault; and `line`, an entry on one
line. It imports the catalogue, whose values every figure here is, and holds no threshold. What the
stream does not carry, the document and the decoder's facts, a text takes as a dict.

    .venv\Scripts\python -m sieve_player.report dump.jsonl
"""
import json
import sys

from .catalogue import Log, alike, cost, gui, machine, needs, rows, size, span, store_name, tight
from .ledger import Total, Under, replay


def report(entries, view, context=None):
    """One block for `entries`, in the order given: the problems numbered, each with its sentence
    and target, its evidence, where the class has come from and its simulation; then once, of the
    first entry's walk, the walk and the one before it in its lane, the plan's watched set, the
    table with the numbers of the problems naming each node, the machine, the GUI thread, the
    stores, the video and the decoder, and the history's file. `context` is as `text` takes it, with
    "history", the path of a saved history holding the document, "when", the wall time as written,
    and "now", the probe's clock; a part with nothing to say reads "-"."""
    c, named = context or {}, {}
    out = [f"SIEVE monitor report · {c.get('when', '-')} · commit {c.get('commit') or '-'}",
           f"{len(entries)} problem{'s' * (len(entries) != 1)}, costliest first; their shares may count the same ms twice"]
    for i, e in enumerate(entries, 1):
        p = e.problem
        since = "" if c.get("now") is None else f" · first seen {c['now'] - e.first:.0f} s before this"
        out += ["", f"{i}  {p.kind} · {p.subject} · {p.ms_row:.2f} ms a row" + ("" if p.share is None else f" · {p.share:.0%}")
                + f" · {e.count} walk{'s' * (e.count != 1)}{since}{'' if e.holds else ' · cleared'}",
                f"   {p.says}: {p.target}", f"   {p.line}", *("   " + x for x in p.evidence),
                f"   from  {p.source}", f"   repro python -m sieve_player.dev.simulations {p.kind}"]
        for n in p.nodes:
            named.setdefault(n, []).append(str(i))

    def said(w):
        return (f"{w.lane} · rows {w.start}..{(w.start or 0) + w.length - 1} · {w.done} done · "
                f"{(cost(w) + w.unprobed) / max(w.done, 1):.2f} ms a row" + (" · under more than one plan" if w.replanned else ""))
    at = next((i for i, w in enumerate(view.walks) if w.id == entries[0].problem.walk), -1) if entries else len(view.walks) - 1
    out.append("")
    if at < 0:
        out.append("WALK     no longer in the history")
    else:
        w = view.walks[at]
        prev = next((x for x in reversed(view.walks[:at]) if x.lane == w.lane), None)
        plan = w.plan or {}
        out += ["WALK     " + said(w),
                "BEFORE   " + ("-" if prev is None else said(prev) + (" · the same plan" if prev.keys == w.keys else " · another plan")),
                "PLAN     " + ("-" if not plan else f"walks {plan.get('walk')} · chain {', '.join(plan.get('chain') or []) or 'none'} · "
                               f"shown {plan.get('shown')} · pinned {', '.join(plan.get('pinned') or []) or 'none'} · "
                               f"selected {', '.join(w.selected) or 'none'}"),
                "", f"ROW      {'node':<16}{'ms/row':>7}{'spans':>7}  {'kind':<7}{'asked by':<20}{'p50':>7}{'p99':>7}{'ms/MP':>7}  in"]

        def ms(x):
            return f"{'-' if x is None else format(x, '.2f'):>7}"
        for r in rows(w, view).values():
            out.append(f"         {r.node:<16}{r.ms_row:>7.2f}{r.spans:>7}  {r.kind:<7}{r.asked_by():<20}{ms(r.median)}{ms(r.p99)}{ms(r.per_mp)}"
                       f"  {','.join(named.get(r.node, []))}".rstrip())
        res, like = machine(view, w), alike(view, w)
        late, turns = gui(view, w)
        stores, need = next((b.stores for b in reversed(span(view, w)) if b.stores), {}), needs(view, w)
        out += [f"         {'unprobed':<16}{w.unprobed / max(w.done, 1):>7.2f}", "",
                "MACHINE  " + "\n         ".join([tight(res), *(f"{r.name} {r.value} · {r.note}" for r in res),
                                                 *([f"{len(like)} walks under this plan and as cold, {min(like):.2f} to {max(like):.2f} ms a row"]
                                                   if len(like) > 1 else [])]),
                f"GUI      worst {late:.0f} ms late · " + " · ".join(("the monitor" if what == "monitor" else f"{what}s") + f" {share:.1%}"
                                                                   + (f", {top} the longest" if top and what != "monitor" else "")
                                                                   for what, share, top in turns),
                "STORES   " + ("\n         ".join(
                    f"{store_name(s, view)} {size(held)} of {size(limit or 0)} · {w.recomputed.get(s, 0)} run again"
                    + (f" · the {w.lane or 'walk'} needs {size(need[s])}" if s in need else "") for s, (held, limit) in stores.items()) or "-")]
    d = c.get("decoder")
    out += [f"VIDEO    {c.get('video', '-')} · " + ("-" if not d else ", ".join(f"{k} {v}" for k, v in d.items())) + f" · memo limit {c.get('memo_limit', '-')}",
            f"HISTORY  {c.get('history') or '-'}"]
    return "\n".join(out)


def line(entry):
    p = entry.problem
    share = "" if p.share is None else f" {p.share:.0%}"
    return (f"{p.kind:<7} {p.subject:<14} {p.ms_row:7.2f} ms/row{share:>5}  x{entry.count}"
            f"{'' if entry.holds else '  cleared'}  {p.line}")


def text(entry, view, context=None):
    """One block sufficient to begin on the entry's fault without the session it was seen in, each
    part under its label, the document last and whole after its label's line. `context` is what
    no view holds: "document", the document as saved, "video", "decoder", "memo_limit", "commit",
    "dump"; a part it lacks reads "-"."""
    p, c = entry.problem, context or {}
    w = next((w for w in view.walks if w.id == p.walk), None)
    out = [f"class      {p.kind}", f"subject    {p.subject}", f"line       {p.line}",
           f"cost       {p.ms_row:.3f} ms a row" + ("" if p.share is None else f", {p.share:.0%} of what the walk's nodes cost")
           + f"; seen in {entry.count} walk{'s' * (entry.count != 1)}, {'still holds' if entry.holds else "in no lane's last walk"}",
           "evidence", *("  " + e for e in p.evidence)]
    if w is None:
        out.append("walk       no longer in the history")
    else:
        out.append(f"walk       {w.lane}, rows {w.start}..{(w.start or 0) + w.length - 1}, {w.done} of {w.length} done in "
                   f"{w.t1 - w.t0:.2f} s, {cost(w):.0f} ms in its nodes" + (", under more than one plan" if w.replanned else ""))
        out.append(f"  {'node':<14}{'ran':>6}{'held':>6}{'served':>7}  {'kind':<7}{'demand':<8}{'asked':<14}{'n':>6}{'ms':>9}{'ms/row':>8}")
        for nid, node in w.nodes.items():
            head = f"  {nid:<14}{node.ran:>6}{node.held:>6}{node.served:>7}  "
            for u, r in node.runs.items() or {Under("-", "-", "-"): Total(0, 0.0, 0)}.items():
                out.append(f"{head}{u.kind:<7}{str(u.demand):<8}{str(u.asked):<14}{r.count:>6}{r.ms:>9.1f}{r.ms / w.done:>8.3f}")
                head = " " * len(head)
        nodes = (w.plan or {}).get("nodes") or {}
        out.append("plan       " + ("-" if not nodes else f"walk {w.plan['walk']}, chain {w.plan['chain']}, shown {w.plan['shown']}, "
                                    f"overlaid {w.plan['over']}, pinned {w.plan['pinned']}, selected {w.selected}"))
        if p.subject in nodes:
            readers = [n for n, f in nodes.items() if p.subject in f["reads"].values()]
            for nid in dict.fromkeys([p.subject, *(s for s in nodes[p.subject]["reads"].values() if s), *readers]):
                f = nodes[nid]
                flags = [f["kind"], "fed" if f["fed"] else "unfed", *(k for k in ("static", "served", "steps") if f[k]),
                         *([f"whole by {f['whole_by']}"] if f["whole_by"] else [])]
                out.append(f"  {nid}: {', '.join(flags)}; reads {', '.join(str(s) for s in f['reads'].values())}; "
                           f"read by {', '.join(n for n, x in nodes.items() if nid in x['reads'].values()) or 'nothing'}")
        names = {k: n for n, k in (w.keys or {}).items()}
        stores = next((b.stores for b in reversed(view.buckets) if b.stores), {})
        out.append("stores     " + (", ".join(f"{'memo' if s == 'memo' else names.get(s, s) + ' cache'} {b / 2**20:.1f} of "
                                              f"{(limit or 0) / 2**20:.1f} MB" for s, (b, limit) in stores.items()) or "-"))
    d = c.get("decoder")
    out += [f"video      {c.get('video', '-')}",
            "decoder    " + ("-" if not d else ", ".join(f"{k} {v}" for k, v in d.items())) + f"; memo limit {c.get('memo_limit', '-')}",
            f"commit     {c.get('commit') or '-'}", f"dump       {c.get('dump') or '-'}",
            f"simulation python -m sieve_player.dev.simulations {p.kind}", f"source     {p.source}",
            "document", json.dumps(c.get("document"), indent=2, ensure_ascii=False)]
    return "\n".join(out)


if __name__ == "__main__":
    log = Log()
    log.read(replay(sys.argv[1]).view())
    print("\n".join(line(e) for e in log.ordered()) or "nothing found")
